import asyncio
import json

import pytest
import yaml
from conftest import VERDICT_PASS, FakeModel, StubTTS, make_plan, make_script, stub_renderer
from PIL import Image

from reelhive.agents.scene_planner import ScenePlannerNode
from reelhive.core.service import Service
from reelhive.schemas.brief import Images, Visuals
from reelhive.schemas.scene_spec import HookScene, HookText, IntroText, VisualAsset, VisualRequest


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


def test_high_brief_with_its_own_scenes_takes_the_intro_from_the_brief(config, brief):
    brief.level = "high"
    brief.cta_url = "costhive.dev"
    brief.scenes = [HookScene(index=1, narration="Hello", text=HookText(headline="Hi"))]
    service = Service(config, {"strong": FakeModel({})}, StubTTS(), stub_renderer)

    brief.intro = IntroText(title="ScanComb", tagline="Next-level platform for IT security and compliance")
    ctx = service.new_run(brief)
    asyncio.run(ScenePlannerNode().execute(ctx))
    assert ctx.spec and ctx.spec.intro
    assert (ctx.spec.intro.title, ctx.spec.intro.url) == ("ScanComb", "costhive.dev")

    brief.intro = None  # no agent runs for explicit scenes, so there is simply no intro
    ctx = service.new_run(brief)
    asyncio.run(ScenePlannerNode().execute(ctx))
    assert ctx.spec and ctx.spec.intro is None


@pytest.mark.parametrize("level", ["low", "medium", "high"])
def test_stopped_run_requires_image_approval_only_for_high(config, brief, level):
    brief.level = "high"
    model = FakeModel(
        {
            "Script": make_script(brief),
            "ScenePlan": make_plan(brief),
            "MusicChoice": {"mood": "tech", "bpm": 110, "reason": "fits"},
            "Verdict": VERDICT_PASS,
        }
    )
    service = Service(config, {"strong": model, "fast": model}, StubTTS(), stub_renderer)
    run_dir = service.run(brief).run_dir
    service.approve(run_dir)
    ctx = service.load(run_dir)
    ctx.brief.level = level
    ctx.brief.visuals = Visuals(source="images", images=Images(dir=str(run_dir)))
    (run_dir / "brief.yaml").write_text(yaml.safe_dump(ctx.brief.model_dump(mode="json")))
    Image.new("RGB", (1920, 1080), "blue").save(run_dir / "sample.png")
    scene = ctx.spec.scenes[0]
    scene.visual_request = VisualRequest(kind="concept", image="sample.png")
    scene.visual = VisualAsset(source="provided", file="sample.png")
    scene.image_approved = False
    ctx.checkpoint()
    (run_dir / "status.json").write_text(json.dumps({"status": "stopped"}))

    if level == "high":
        with pytest.raises(ValueError, match="approve every scene image"):
            service.approve_scenes(run_dir)
    else:
        result = service.approve_scenes(run_dir)
        assert result.status == "done"
        assert result.video and result.video.is_file()
        saved = json.loads((run_dir / "spec.json").read_text())
        assert saved["scenes"][0]["visual"] is not None
        assert saved["scenes"][0]["image_approved"] is False  # no fabricated user approval


def test_saving_scenes_keeps_the_intro_words_editable_but_not_its_address(config, brief):
    brief.level = "high"
    brief.cta_url = "costhive.dev"
    draft = FakeModel({"Script": make_script(brief)})
    tts = StubTTS()
    first = Service(config, {"strong": draft}, tts, stub_renderer).run(brief)
    music = {"mood": "tech", "bpm": 110, "reason": "fits"}
    production = FakeModel({"ScenePlan": make_plan(brief), "MusicChoice": music})
    service = Service(config, {"strong": production, "fast": production}, tts, stub_renderer)
    assert service.approve(first.run_dir).status == "awaiting_scenes"
    edited = service.load(first.run_dir).spec
    assert edited and edited.intro and edited.intro.url == "costhive.dev"  # visible while the user reviews
    edited.intro.title = "CostHive Pro"
    edited.intro.url, edited.intro.duration = "evil.example", 9.0

    service.save_spec(first.run_dir, edited)
    saved = service.load(first.run_dir).spec
    assert saved and saved.intro
    assert (saved.intro.title, saved.intro.url, saved.intro.duration) == ("CostHive Pro", "costhive.dev", 3.0)
    assert saved.scenes[0].start == 3.0
