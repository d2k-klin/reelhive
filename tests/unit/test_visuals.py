import json

import pytest
from PIL import Image
from pydantic import ValidationError

from reelhive.agents.critic import hard_checks
from reelhive.core.context import RunContext
from reelhive.core.events import EventBus
from reelhive.schemas.brief import Brand, Generate, Images, Screenshots, Visuals
from reelhive.schemas.scene_spec import HookText, ImageScene, SceneSpec, VisualAsset, VisualRequest
from reelhive.visuals import provided
from reelhive.visuals.capture import same_origin
from reelhive.visuals.resolver import catalog, image_ok, local_asset, resolve, theme_for


@pytest.fixture
def ctx(tmp_path, brief, config):
    return RunContext(tmp_path, brief, EventBus(), {}, None, None, config=config)


def png(path, size=(1920, 1920)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, "red").save(path)
    return path


def scene(kind="concept", **request):
    return ImageScene(
        index=1,
        narration="dashboard",
        text=HookText(headline="Dashboard"),
        visual_request=VisualRequest(kind=kind, **request),
    )


class FakeImageGenerator:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def generate(self, prompt, size, output):
        self.calls.append((prompt, size))
        if self.fail:
            raise RuntimeError("provider unavailable")
        png(output)
        return {"cost_usd": 0.01, "usage": {"total_tokens": 10}}


@pytest.mark.parametrize("kind", ["product_ui", "concept"])
def test_provided_wins_over_other_sources(ctx, kind, monkeypatch):
    folder = ctx.run_dir / "input"
    png(folder / "dashboard.png")
    (folder / "captions.yaml").write_text("dashboard.png: account overview\n")
    ctx.brief.visuals = Visuals(images=Images(dir=str(folder)), generate=True)
    ctx.visual_catalog = catalog(ctx)
    ctx.spec = SceneSpec(scenes=[scene(kind, image="dashboard.png", prompt="dashboard")])
    generator = FakeImageGenerator()
    resolve(ctx, generator)
    assert ctx.spec.scenes[0].visual.source == "provided"
    assert not generator.calls
    assert provided.match(ctx.visual_catalog, None, "account")["image"] == "dashboard.png"
    assert provided.match(ctx.visual_catalog, "../../secret.png", "dashboard") is None
    assert provided.match([], None, "missing") is None
    assert provided.match(ctx.visual_catalog, None, "unrelated") is None


@pytest.mark.parametrize(
    "kind,source,expected",
    [
        ("product_ui", "generate", None),
        ("product_ui", "auto", None),
        ("concept", "generate", "generated"),
        ("concept", "auto", "generated"),
        ("concept", "none", None),
        ("none", "auto", None),
    ],
)
def test_generation_matrix(ctx, kind, source, expected):
    ctx.brief.visuals = Visuals(source=source, generate=True)
    ctx.spec = SceneSpec(scenes=[scene(kind, prompt="abstract clouds")])
    generator = FakeImageGenerator()
    resolve(ctx, generator)
    result = ctx.spec.scenes[0]
    assert (result.visual.source if result.visual else None) == expected
    if expected is None:
        assert result.template == "hook" and not generator.calls


def test_generation_cache_cap_and_style(ctx):
    ctx.brief.visuals = Visuals(generate=Generate(max_images=1, style="paper cut"))
    ctx.brief.brand = Brand(colors=["#123456"])
    ctx.spec = SceneSpec(scenes=[scene(prompt="one")])
    generator = FakeImageGenerator()
    resolve(ctx, generator)
    original = ctx.spec.scenes[0].visual.file
    ctx.spec = SceneSpec(scenes=[scene(prompt="one")])
    resolve(ctx, generator)
    assert len(generator.calls) == 1 and ctx.spec.scenes[0].visual.file == original
    assert "paper cut" in generator.calls[0][0] and "#123456" in generator.calls[0][0]
    ctx.spec = SceneSpec(scenes=[scene(prompt="two")])
    resolve(ctx, generator)
    assert ctx.spec.scenes[0].template == "hook" and len(generator.calls) == 1
    record = json.loads((ctx.run_dir / "visuals/generated.json").read_text())
    assert next(iter(record.values()))["cost_usd"] == 0.01


def test_failed_generation_counts_toward_cap(ctx):
    ctx.brief.visuals = Visuals(generate=Generate(max_images=1))
    generator = FakeImageGenerator(fail=True)
    for prompt in ("first", "first", "second"):
        ctx.spec = SceneSpec(scenes=[scene(prompt=prompt)])
        resolve(ctx, generator)
        assert ctx.spec.scenes[0].visual is None
    assert len(generator.calls) == 1


def test_missing_generation_config_falls_back(ctx):
    ctx.brief.visuals = Visuals(generate=True)
    ctx.spec = SceneSpec(scenes=[scene(prompt="idea")])
    resolve(ctx)
    assert ctx.spec.scenes[0].template == "hook"


def test_screenshot_fallback_and_frame(ctx, monkeypatch):
    ctx.brief.visuals = Visuals(screenshots=Screenshots(url="http://localhost:1234", frame="browser"))
    monkeypatch.setattr("reelhive.visuals.capture.discover", lambda *_: [{"route": "/dashboard"}])
    monkeypatch.setattr("reelhive.visuals.capture.capture", lambda *args: png(args[-1]))
    ctx.visual_catalog = catalog(ctx)
    ctx.spec = SceneSpec(scenes=[scene("product_ui")])
    resolve(ctx)
    asset = ctx.spec.scenes[0].visual
    assert (asset.source, asset.frame) == ("screenshot", "browser")
    resolve(ctx)  # a resolved asset is reused
    assert ctx.spec.scenes[0].visual == asset

    def broken(*_):
        raise RuntimeError("offline")

    monkeypatch.setattr("reelhive.visuals.capture.capture", broken)
    monkeypatch.setattr("reelhive.visuals.capture.discover", broken)
    assert catalog(ctx) == []
    ctx.spec = SceneSpec(scenes=[scene("product_ui")])
    resolve(ctx)
    assert ctx.spec.scenes[0].template == "hook"


def test_resolution_and_path_gates(ctx):
    path = png(ctx.run_dir / "image.png", (100, 100))
    assert not image_ok(path, "16:9")
    assert not image_ok(ctx.run_dir / "missing", "16:9")
    ctx.spec = SceneSpec(scenes=[scene("product_ui")])
    ctx.spec.scenes[0].visual = VisualAsset(source="generated", file="image.png")
    gates = {c.name: c.passed for c in hard_checks(ctx.spec, ctx.brief, {}, ctx.run_dir)}
    assert not gates["images"] and not gates["product_ui"]
    ctx.spec.scenes[0].visual.file = "../outside.png"
    assert not next(c for c in hard_checks(ctx.spec, ctx.brief, {}, ctx.run_dir) if c.name == "images").passed
    with pytest.raises(ValueError, match="inside"):
        local_asset(ctx.run_dir, "../outside")
    png(path)
    assert image_ok(path, "9:16")


def test_theme_and_logo_copied_to_run(ctx):
    ctx.brief.theme = "dark"
    ctx.brief.brand = Brand(colors=["#112233", "#223344", "#FFFFFF"], logo=str(png(ctx.run_dir / "logo.png")))
    theme = theme_for(ctx)
    assert (theme.accent, theme.background, theme.text) == ("#112233", "#223344", "#FFFFFF")
    assert (ctx.run_dir / theme.logo).exists()


def test_catalog_validation_and_shortcuts(tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        provided.catalog(Images(dir=str(tmp_path / "absent")))
    (tmp_path / "captions.yaml").write_text("- invalid\n")
    with pytest.raises(ValueError, match="map filenames"):
        provided.catalog(Images(dir=str(tmp_path)))
    opts = Visuals(url="http://localhost:8080", images=str(tmp_path), generate=True)
    assert opts.screenshots and isinstance(opts.images, Images) and isinstance(opts.generate, Generate)
    for data in (
        {"source": "images"},
        {"url": "file:///tmp"},
        {"url": "http://localhost", "screenshots": {"url": "http://localhost"}},
    ):
        with pytest.raises(ValidationError):
            Visuals(**data)


@pytest.mark.parametrize(
    "route", ["https://elsewhere.test", "//elsewhere.test", "file:///tmp", "http://localhost:9999"]
)
def test_capture_rejects_cross_origin(route):
    with pytest.raises(ValueError):
        same_origin("http://localhost:1234", route)
    assert same_origin("http://localhost:1234", "/home#top") == "http://localhost:1234/home"


def test_describe_is_explicit_and_sends_only_catalog_images(ctx, monkeypatch):
    import asyncio
    from types import SimpleNamespace

    calls = []

    class Agent:
        def __init__(self, **kwargs):
            pass

        async def invoke_async(self, content):
            calls.append(content)
            return SimpleNamespace(metrics=SimpleNamespace(accumulated_usage={"totalTokens": 5}))

    monkeypatch.setattr("strands.Agent", Agent)
    file = png(ctx.run_dir / "dashboard.png")
    ctx.visual_catalog = [{"image": file.name, "file": str(file), "caption": ""}, {"route": "/dashboard"}]
    asyncio.run(provided.describe(ctx))
    assert len(calls) == 1 and calls[0][1]["image"]["source"]["bytes"] == file.read_bytes()
    ctx.config.provider = "copilot"
    with pytest.raises(RuntimeError, match="vision provider"):
        asyncio.run(provided.describe(ctx))
