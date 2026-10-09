"""Both graphs end to end with FakeModel, StubTTS and an ffmpeg stand-in for Revideo."""

import copy
import json

import pytest
from conftest import VERDICT_PASS, FakeModel, StubTTS, make_plan, make_script, stub_renderer, words

from reelhive.audio.mixer import probe
from reelhive.core.events import replay
from reelhive.core.service import Service
from reelhive.schemas.scene_spec import CREDIT_TEXT

MUSIC = {"mood": "tech", "bpm": 110, "reason": "fits a developer audience"}


def service(config, responses):
    model = FakeModel(responses)
    tts = StubTTS()
    return Service(config, models={"strong": model, "fast": model}, tts=tts, renderer=stub_renderer), model, tts


def run(svc, brief):
    events = []
    result = svc.run(brief, on_event=events.append)
    return result, events


def of_type(events, type_):
    return [e.data for e in events if e.type == type_]


def test_pass_path_renders_a_video(config, brief):
    svc, model, tts = service(
        config,
        {"Script": make_script(brief), "ScenePlan": make_plan(brief), "MusicChoice": MUSIC, "Verdict": VERDICT_PASS},
    )
    result, events = run(svc, brief)

    assert result.status == "done"
    info = probe(result.video)
    assert info["has_audio"] and info["comment"] == CREDIT_TEXT
    assert info["duration"] == pytest.approx(brief.duration, rel=0.05)
    assert sorted(model.calls) == ["MusicChoice", "ScenePlan", "Script", "Verdict"]
    assert len(tts.calls) == 6

    started = [d["node"] for d in of_type(events, "node.started")]
    assert started[:2] == ["brief", "script"]
    assert set(started[2:5]) == {"scenes", "narrate", "music"}  # parallel branches
    assert started[5:] == ["visuals", "timing", "critic", "render"]
    assert [d["node"] for d in of_type(events, "node.skipped")] == ["fix", "recheck"]
    assert all(d["passed"] for d in of_type(events, "gate.result"))
    assert of_type(events, "critic.verdict")[0]["passed"]
    assert any(d["node"] == "script" for d in of_type(events, "agent.text"))
    assert of_type(events, "run.finished")[0]["status"] == "done"
    assert {d["node"]: d["tokens"] for d in of_type(events, "node.finished")}["script"] == 150

    run_dir = result.run_dir
    for name in ("brief.yaml", "script.json", "spec.json", "audio/mix.wav", "video.mp4", "run.log.jsonl"):
        assert (run_dir / name).exists(), name
    spec = json.loads((run_dir / "spec.json").read_text())
    assert spec["credit"]["mode"] == "end" and spec["music"].endswith("tech-110.mp3")
    assert [e.type for e in replay(run_dir / "run.log.jsonl")] == [e.type for e in events]


def test_hard_check_failure_takes_the_fix_path(config, brief):
    script = make_script(brief)
    fixed_narration = [b["narration"] for b in script["beats"]]
    fixed_narration[2] = words(23, brief.features[0])  # fixer rewords the uncovered feature's beat
    svc, model, tts = service(
        config,
        {
            "Script": script,
            "ScenePlan": [make_plan(brief, drop_feature=1), make_plan(brief, narration=fixed_narration)],
            "MusicChoice": MUSIC,
        },
    )
    result, events = run(svc, brief)

    assert result.status == "done"
    assert "Verdict" not in model.calls  # hard checks failed, so no LLM review
    gates = of_type(events, "gate.result")
    assert {(d["node"], d["check"]) for d in gates if not d["passed"]} == {("critic", "features")}
    assert all(d["passed"] for d in gates if d["node"] == "recheck")
    diff = of_type(events, "fix.diff")[0]["changes"]
    assert [c["scene"] for c in diff] == [3]
    assert len(tts.calls) == 7  # six beats + the one re-voiced scene
    assert of_type(events, "node.skipped") == []


def test_recheck_failure_stops_with_a_report(config, brief):
    broken = make_plan(brief, drop_feature=2)
    svc, _, _ = service(
        config, {"Script": make_script(brief), "ScenePlan": [broken, copy.deepcopy(broken)], "MusicChoice": MUSIC}
    )
    result, events = run(svc, brief)

    assert result.status == "stopped" and result.video is None
    assert any("features not covered" in line and brief.features[1] in line for line in result.report)
    assert [d["node"] for d in of_type(events, "node.skipped")] == ["render"]
    assert of_type(events, "run.finished")[0]["status"] == "stopped"


def test_critic_rejection_goes_through_fix(config, brief):
    script = make_script(brief)
    narration = [b["narration"] for b in script["beats"]]
    verdict = {**VERDICT_PASS, "hook": 2, "passed": False, "reasons": ["hook is flat"]}
    svc, model, _ = service(
        config,
        {
            "Script": script,
            "ScenePlan": [make_plan(brief), make_plan(brief, narration=narration)],
            "MusicChoice": MUSIC,
            "Verdict": verdict,
        },
    )
    result, events = run(svc, brief)
    assert result.status == "done"
    assert of_type(events, "critic.verdict")[0]["reasons"] == ["hook is flat"]
    assert of_type(events, "fix.diff")[0]["changes"] == []


def test_disabling_the_credit_keeps_the_metadata_tag(config, brief, monkeypatch):
    monkeypatch.setenv("REELHIVE_DISABLE_CREDIT", "true")
    svc, _, _ = service(
        config,
        {
            "Script": make_script(brief, total_words=145),
            "ScenePlan": make_plan(brief),
            "MusicChoice": MUSIC,
            "Verdict": VERDICT_PASS,
        },
    )
    result, events = run(svc, brief)
    assert json.loads((result.run_dir / "spec.json").read_text())["credit"] is None
    assert any("credit disabled" in d["task"] for d in of_type(events, "node.task"))  # plan §3.7: logged
    assert probe(result.video)["comment"] == CREDIT_TEXT


def test_node_errors_fail_the_run(config, brief):
    plan = make_plan(brief)
    plan["scenes"].pop()  # one scene short of the beats
    svc, _, _ = service(config, {"Script": make_script(brief), "ScenePlan": plan, "MusicChoice": MUSIC})
    events = []
    with pytest.raises(Exception, match="returned 5 scenes for 6 beats"):
        svc.run(brief, on_event=events.append)
    assert of_type(events, "run.finished")[0]["status"] == "failed"


def test_preview_renders_one_scene_silently(config, brief):
    svc, _, _ = service(
        config,
        {"Script": make_script(brief), "ScenePlan": make_plan(brief), "MusicChoice": MUSIC, "Verdict": VERDICT_PASS},
    )
    result, _ = run(svc, brief)
    out = svc.preview_scene(result.run_dir, 2)
    assert out == result.run_dir / "previews" / "scene_02.mp4"
    scene = json.loads((result.run_dir / "spec.json").read_text())["scenes"][1]
    assert probe(out)["duration"] == pytest.approx(scene["duration"], abs=0.1)
    assert not list(result.run_dir.glob(".preview_*.json"))  # the temporary spec is cleaned up
    with pytest.raises(ValueError, match="scene 99 does not exist"):
        svc.preview_scene(result.run_dir, 99)


def test_render_progress_is_logged_per_percent_not_per_frame(config, brief):
    def chatty_renderer(spec, out, on_progress):
        for frame in range(2700):  # a 90s video at 30 fps reports every frame
            on_progress(frame / 2699)
        stub_renderer(spec, out, lambda _: None)

    model = FakeModel(
        {"Script": make_script(brief), "ScenePlan": make_plan(brief), "MusicChoice": MUSIC, "Verdict": VERDICT_PASS}
    )
    svc = Service(config, models={"strong": model, "fast": model}, tts=StubTTS(), renderer=chatty_renderer)
    result, events = run(svc, brief)
    frames = [d for d in of_type(events, "node.task") if d["task"] == "Rendering frames"]
    assert result.status == "done" and len(frames) == 101  # 0% .. 100%
