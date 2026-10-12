"""The user's own clips: catalogued with their length, normalized once, played in a scene, and gated."""

import subprocess

import pytest

from reelhive.agents.critic import hard_checks
from reelhive.audio.mixer import ffmpeg_exe, probe
from reelhive.core.context import RunContext
from reelhive.core.events import EventBus
from reelhive.schemas.brief import Images, Visuals
from reelhive.schemas.scene_spec import HookText, ImageScene, SceneSpec, VisualAsset, VisualRequest
from reelhive.visuals import clips, provided
from reelhive.visuals.resolver import catalog, resolve, visual_ok


def clip(path, size="1280x720", seconds=1.5, rotate=None):
    """A test-pattern video with a sound track, like a screen recording with its microphone on."""
    path.parent.mkdir(parents=True, exist_ok=True)
    args = [ffmpeg_exe(), "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=s={size}:r=24:d={seconds}"]
    args += ["-f", "lavfi", "-i", f"sine=d={seconds}", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)]
    subprocess.run(args, check=True)
    if rotate:
        turned = path.with_name("turned" + path.suffix)
        subprocess.run(
            [
                ffmpeg_exe(),
                "-loglevel",
                "error",
                "-y",
                "-display_rotation",
                str(rotate),
                "-i",
                str(path),
                "-c",
                "copy",
                str(turned),
            ],
            check=True,
        )
        turned.replace(path)
    return path


@pytest.fixture
def ctx(tmp_path, brief, config):
    return RunContext(tmp_path / "run", brief, EventBus(), {}, None, None, config=config)


def scene(**request):
    return ImageScene(
        index=1,
        narration="watch it work",
        text=HookText(headline="Watch it work"),
        visual_request=VisualRequest(kind="product_ui", **request),
    )


def test_catalog_lists_clips_with_length_size_and_a_poster(tmp_path):
    folder = tmp_path / "input"
    clip(folder / "demo.mov")
    (folder / "captions.yaml").write_text("demo.mov: creating a report in two clicks\n")
    [entry] = provided.catalog(Images(dir=str(folder)), tmp_path / "posters")
    assert entry["clip"] == "demo.mov" and entry["caption"].startswith("creating")
    assert entry["duration"] == pytest.approx(1.5, abs=0.1) and (entry["width"], entry["height"]) == (1280, 720)
    assert (tmp_path / "posters/demo.jpg").stat().st_size > 0


def test_a_phone_recording_is_measured_upright(tmp_path):
    info = clips.inspect(clip(tmp_path / "phone.mov", size="1280x720", rotate=90))
    assert (info["width"], info["height"]) == (720, 1280)


def test_unplayable_or_unsupported_files_are_rejected(tmp_path):
    (tmp_path / "broken.mp4").write_bytes(b"not a video")
    with pytest.raises(clips.ClipError, match="not a playable video"):
        clips.inspect(tmp_path / "broken.mp4")
    (tmp_path / "clip.avi").write_bytes(b"")
    with pytest.raises(clips.ClipError, match="clips must be"):
        clips.inspect(tmp_path / "clip.avi")


def test_the_planners_clip_is_normalized_into_the_run_and_passes_the_gates(ctx):
    folder = ctx.run_dir / "input"
    clip(folder / "demo.mov", size="1920x1080")
    ctx.brief.visuals = Visuals(images=Images(dir=str(folder)))
    ctx.visual_catalog = catalog(ctx)
    ctx.spec = SceneSpec(scenes=[scene(clip="demo.mov")])
    resolve(ctx)
    visual = ctx.spec.scenes[0].visual
    assert visual.media == "video" and visual.file == "visuals/clips/scene_01.mp4"
    info = probe(ctx.run_dir / visual.file)
    assert not info["has_audio"] and (info["width"], info["height"]) == (1920, 1080)
    assert visual_ok(ctx.run_dir, visual, "16:9")
    images = next(c for c in hard_checks(ctx.spec, ctx.brief, {}, ctx.run_dir) if c.name == "images")
    assert images.passed


def test_normalizing_again_reuses_the_clip(ctx, monkeypatch):
    source = clip(ctx.run_dir / "input/demo.mp4")
    dest = ctx.run_dir / "visuals/clips/scene_01.mp4"
    first = clips.normalize(source, dest, "16:9")
    monkeypatch.setattr(clips.subprocess, "run", lambda *a, **k: pytest.fail("re-encoded an unchanged clip"))
    assert clips.normalize(source, dest, "16:9") == first


def test_a_clip_is_never_enlarged_and_a_soft_one_falls_back(ctx):
    folder = ctx.run_dir / "input"
    clip(folder / "tiny.mp4", size="640x360")
    ctx.brief.visuals = Visuals(images=Images(dir=str(folder)))
    ctx.visual_catalog = catalog(ctx)
    ctx.spec = SceneSpec(scenes=[scene(clip="tiny.mp4")])
    resolve(ctx)
    assert ctx.spec.scenes[0].visual is None and ctx.spec.scenes[0].template == "hook"  # text fallback
    assert (clips.inspect(ctx.run_dir / "visuals/clips/scene_01.mp4")["width"]) == 640


def test_an_unknown_clip_name_is_not_guessed(ctx):
    folder = ctx.run_dir / "input"
    clip(folder / "demo.mp4")
    ctx.brief.visuals = Visuals(images=Images(dir=str(folder)))
    ctx.visual_catalog = catalog(ctx)
    ctx.spec = SceneSpec(scenes=[scene(clip="other.mp4")])
    resolve(ctx)
    assert ctx.spec.scenes[0].visual is None


def test_a_video_visual_must_carry_its_measurements():
    with pytest.raises(ValueError, match="duration, width and height"):
        VisualAsset(source="provided", media="video", file="visuals/clips/scene_01.mp4")
