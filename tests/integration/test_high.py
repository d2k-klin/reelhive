import json

from conftest import VERDICT_PASS, FakeModel, StubTTS, make_plan, make_script, stub_renderer

from reelhive.core.service import Service


def test_high_run_pauses_for_script_and_scenes_then_renders(config, brief):
    brief.level = "high"
    draft = FakeModel({"Script": make_script(brief)})
    tts = StubTTS()
    first = Service(config, {"strong": draft}, tts, stub_renderer).run(brief)
    assert first.status == "awaiting_script"

    production = FakeModel(
        {
            "ScenePlan": make_plan(brief),
            "MusicChoice": {"mood": "tech", "bpm": 110, "reason": "fits"},
            "Verdict": VERDICT_PASS,
        }
    )
    service = Service(config, {"strong": production, "fast": production}, tts, stub_renderer)
    prepared = service.approve(first.run_dir)
    assert prepared.status == "awaiting_scenes"
    assert json.loads((first.run_dir / "status.json").read_text())["status"] == "awaiting_scenes"
    assert (first.run_dir / "spec.json").exists() and not (first.run_dir / "video.mp4").exists()

    finished = service.approve_scenes(first.run_dir)
    assert finished.status == "done"
    assert finished.video and finished.video.exists()


def test_high_explicit_scene_voice_is_used_before_parallel_planner(config, brief):
    from reelhive.nodes.narrate_node import narrate
    from reelhive.schemas.scene_spec import HookScene, HookText
    from reelhive.schemas.voice import Voice

    brief.level = "high"
    brief.scenes = [
        HookScene(
            index=1,
            narration="A different voice",
            text=HookText(headline="Listen"),
            voice_override=Voice(gender="male", accent="uk", speed=1.1),
        )
    ]
    tts = StubTTS()
    service = Service(config, {"strong": FakeModel({})}, tts, stub_renderer)
    context = service.new_run(brief)
    narrate(context, 1, brief.scenes[0].narration)
    assert context.voiced[1] == {"gender": "male", "accent": "uk", "speed": 1.1}
