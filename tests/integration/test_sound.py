"""The `sound` node end to end: it scores the reviewed cut on the moments the renderer reported (fake model)."""

import json

from conftest import VERDICT_PASS, FakeModel, StubTTS, make_plan, make_script, stub_renderer

from reelhive.core.service import Service
from reelhive.render.bridge import layout_path
from reelhive.schemas.layout import LayoutReport, Moment
from reelhive.schemas.scene_spec import SceneSpec

MUSIC = {"mood": "tech", "bpm": 110, "reason": "fits"}


def renderer_with_moments(spec, out, on_progress):
    """The ffmpeg stand-in, reporting a cut at the start of every scene and a landing 0.8 s later, as Revideo does."""
    stub_renderer(spec, out, on_progress)
    timeline = SceneSpec.model_validate_json(spec.read_text())
    report = LayoutReport.model_validate_json(layout_path(out).read_text())
    scenes = {s.index: s for s in timeline.scenes}
    for shot in report.shots:
        if shot.kind == "scene":
            start = scenes[shot.index].start
            shot.moments = [
                Moment(kind="cut", at=start, detail="push" if shot.index > 1 else "open"),
                Moment(kind="arrive", at=start + 0.8, detail=scenes[shot.index].template),
            ]
    layout_path(out).write_text(report.model_dump_json())


def produce(config, brief, sound_plans):
    model = FakeModel(
        {
            "Script": make_script(brief),
            "ScenePlan": make_plan(brief),
            "MusicChoice": MUSIC,
            "Verdict": VERDICT_PASS,
            "SoundPlan": sound_plans,
        }
    )
    events = []
    result = Service(config, {"strong": model, "fast": model}, StubTTS(), renderer_with_moments).run(
        brief, events.append
    )
    return result, events, model


def test_the_cut_is_scored_on_reported_moments_and_mixed(config, brief):
    last = len(brief.features) + 3
    plan = {
        "cues": [{"moment": f"scene {last} arrive", "effect": "chime-bright", "gain_db": -26, "reason": "the close"}],
        "reason": "one accent on the call to action",
    }
    result, events, model = produce(config, brief, plan)

    assert result.status == "done" and model.calls.count("SoundPlan") == 1
    spec = json.loads((result.run_dir / "spec.json").read_text())
    [cue] = spec["sound_effects"]
    closing = next(s for s in spec["scenes"] if s["index"] == last)
    assert cue["effect"] == "chime-bright.wav" and cue["at"] == round(closing["start"] + 0.8 - 0.008, 3)
    assert (result.run_dir / "audio/effects.wav").exists()
    tasks = [e.data["task"] for e in events if e.type == "node.task" and e.data["node"] == "sound"]
    assert tasks == [f"1 sound effects: chime-bright on scene {last} arrive"]


def test_a_plan_that_breaks_the_rules_is_repaired_by_the_model(config, brief):
    crowded = {
        "cues": [
            {"moment": "scene 2 cut", "effect": "whoosh-soft", "gain_db": -18, "reason": "r"},
            {"moment": "scene 2 arrive", "effect": "pop-soft", "gain_db": -18, "reason": "r"},
        ],
        "reason": "busy",
    }
    result, events, model = produce(config, brief, [crowded, {"cues": [], "reason": "the voice carries it"}])
    assert result.status == "done" and model.calls.count("SoundPlan") == 2
    assert json.loads((result.run_dir / "spec.json").read_text())["sound_effects"] == []
    assert not (result.run_dir / "audio/effects.wav").exists()


def test_the_brief_can_turn_effects_off(config, brief):
    brief.sound_effects = False
    result, events, model = produce(config, brief, [])
    assert result.status == "done" and "SoundPlan" not in model.calls
