"""The review loop: the rendered cut is judged and repaired through fix -> recheck -> render (fake model)."""

import json

from conftest import VERDICT_PASS, FakeModel, StubTTS, make_plan, make_script, stub_renderer

from reelhive.agents.reviewer import MAX_REVIEW_ROUNDS
from reelhive.core.service import Service
from reelhive.render.bridge import layout_path
from reelhive.schemas.layout import Box, LayoutReport

MUSIC = {"mood": "tech", "bpm": 110, "reason": "fits"}
FRAMES_PASS = {"focal_point": 4, "hierarchy": 4, "readability": 4, "composition": 4, "consistency": 4, "passed": True}
FRAMES_FAIL = {
    **FRAMES_PASS,
    "composition": 2,
    "passed": False,
    "reasons": ["Scene 3: the page is too small; close in"],
}


def renderer_with_bad_cuts(bad: int):
    """The ffmpeg stand-in, whose first `bad` cuts measure a subline running off the left edge of the last scene."""
    renders: list[int] = []

    def render(spec, out, on_progress):
        stub_renderer(spec, out, on_progress)
        renders.append(1)
        if len(renders) <= bad:
            report = LayoutReport.model_validate_json(layout_path(out).read_text())
            report.shots[-1].boxes.append(Box(role="subline", x=-40, y=500, width=600, height=40, font_size=40))
            layout_path(out).write_text(report.model_dump_json())

    return render, renders


def produce(config, brief, renderer, extra=None):
    responses = {
        "Script": make_script(brief),
        "ScenePlan": [make_plan(brief), *[make_plan(brief) for _ in range(MAX_REVIEW_ROUNDS + 1)]],
        "MusicChoice": MUSIC,
        "Verdict": VERDICT_PASS,
        **(extra or {}),
    }
    model = FakeModel(responses)
    events = []
    result = Service(config, {"strong": model, "fast": model}, StubTTS(), renderer).run(brief, events.append)
    return result, events, model


def started(events):
    return [e.data["node"] for e in events if e.type == "node.started"]


def test_a_clipped_cut_is_repaired_and_rendered_again(config, brief):
    renderer, renders = renderer_with_bad_cuts(1)
    result, events, model = produce(config, brief, renderer)

    assert result.status == "done" and result.video
    assert started(events)[-9:] == [
        "critic",
        "render",
        "review",
        "fix",
        "recheck",
        "render",
        "review",
        "sound",
        "master",
    ]
    assert len(renders) == 2 and model.calls.count("ScenePlan") == 2  # planner, then the fixer
    gates = [e.data for e in events if e.type == "gate.result" and e.data["check"] == "safe_area"]
    assert [g["passed"] for g in gates] == [False, True]
    checkpoint = json.loads((result.run_dir / "checkpoint.json").read_text())
    assert checkpoint["review_passed"] is True and checkpoint["review_rounds"] == 1
    assert "master" in checkpoint["completed"]


def test_review_stops_the_run_after_its_last_repair_round(config, brief):
    renderer, renders = renderer_with_bad_cuts(99)
    result, events, _ = produce(config, brief, renderer)

    assert result.status == "stopped" and result.video is None
    assert len(renders) == MAX_REVIEW_ROUNDS + 1
    assert any("safe area" in line for line in result.report)
    assert "master" not in started(events)


def test_frame_review_shows_every_settled_frame_to_a_vision_agent(config, brief):
    brief.frame_review = True
    seen: list[list[dict]] = []

    class Vision(FakeModel):
        async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
            if tool_specs[0]["name"] == "FrameVerdict":
                seen.append([c for m in messages if m["role"] == "user" for c in m["content"]])
            async for event in super().stream(messages, tool_specs, system_prompt, **kwargs):
                yield event

    model = Vision(
        {
            "Script": make_script(brief),
            "ScenePlan": [make_plan(brief), make_plan(brief)],
            "MusicChoice": MUSIC,
            "Verdict": VERDICT_PASS,
            "FrameVerdict": [FRAMES_FAIL, FRAMES_PASS],
        }
    )
    events = []
    result = Service(config, {"strong": model, "fast": model}, StubTTS(), stub_renderer).run(brief, events.append)

    assert result.status == "done"
    verdicts = [e.data for e in events if e.type == "review.verdict"]
    assert [v["passed"] for v in verdicts] == [False, True]
    assert verdicts[0]["reasons"] == ["Scene 3: the page is too small; close in"]
    spec = json.loads((result.run_dir / "spec.json").read_text())
    shots = len(spec["scenes"]) + 1  # every scene and the intro screen
    assert sum("image" in block for block in seen[0]) == shots
    assert (result.run_dir / "render" / "frames" / "intro.jpg").exists()
