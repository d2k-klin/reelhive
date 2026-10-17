"""Real Revideo: a photo story fills the frame, keeps its captions in the safe area, opens settled, dissolves from
photo to photo, and shows a phone's sideways-stored portrait upright."""

import subprocess

import pytest
from PIL import Image

from reelhive.agents.reviewer import layout_checks
from reelhive.audio.mixer import ffmpeg_exe
from reelhive.render.bridge import layout_path, render
from reelhive.schemas.layout import LayoutReport
from reelhive.schemas.scene_spec import (
    PLATFORM_SAFE_AREAS,
    Motion,
    PhotoScene,
    PhotoText,
    SceneSpec,
    VisualAsset,
    Word,
)
from reelhive.visuals.provided import copy_upright

pytestmark = pytest.mark.slow


def frame(video, at, out) -> Image.Image:
    subprocess.run(
        [ffmpeg_exe(), "-v", "error", "-ss", str(at), "-i", str(video), "-frames:v", "1", str(out)], check=True
    )
    return Image.open(out).convert("RGB")


def test_a_photo_story_renders_full_frame_upright_and_readable(tmp_path):
    # A red photo, and a green one stored sideways (as a phone does) with a white band along its real top.
    Image.new("RGB", (2400, 1800), "#c0392b").save(tmp_path / "red.jpg", quality=92)
    green = Image.new("RGB", (2400, 1800), "#27ae60")
    green.paste((255, 255, 255), (0, 0, 2400, 120))
    exif = Image.Exif()
    exif[0x0112] = 6
    green.rotate(90, expand=True).save(tmp_path / "phone.jpg", quality=92, exif=exif)
    (tmp_path / "visuals").mkdir()
    copy_upright(tmp_path / "red.jpg", tmp_path / "visuals" / "one.jpg")
    copy_upright(tmp_path / "phone.jpg", tmp_path / "visuals" / "two.jpg")
    words = [Word(text=w, start=0.3 + i * 0.3, end=0.5 + i * 0.3) for i, w in enumerate("here we see them".split())]
    spec = SceneSpec(
        format="9:16",
        width=1080,
        height=1920,
        duration=6,
        captions=True,
        safe_area=PLATFORM_SAFE_AREAS["reels"],
        motion=Motion(open=0.0),
        scenes=[
            PhotoScene(
                index=1, narration="x", start=0, duration=3, motion="push_in", words=words,
                text=PhotoText(headline="Day one. Optimism.", subline="Lisbon, June 2024"),
                visual=VisualAsset(source="provided", file="visuals/one.jpg"),
            ),
            PhotoScene(
                index=2, narration="x", start=3, duration=3, motion="pull_out", text=PhotoText(),
                visual=VisualAsset(source="provided", file="visuals/two.jpg"),
            ),
        ],
    )  # fmt: skip
    (tmp_path / "spec.json").write_text(spec.model_dump_json())
    video = tmp_path / "render" / "silent.mp4"
    render(tmp_path / "spec.json", video, lambda _: None)

    report = LayoutReport.model_validate_json(layout_path(video).read_text())
    assert not {c.name: c.message for c in layout_checks(report, spec) if not c.passed}
    cover = max(1080 / 2400, 1920 / 1800)  # a landscape photo is enlarged to fill the tall frame
    assert [shot.zoom for shot in report.shots] == pytest.approx([cover * 1.12] * 2, abs=0.01)  # under the 1.35 gate

    first = frame(video, 0, tmp_path / "first.png")
    assert first.getpixel((40, 40))[0] > 150  # the photo reaches the corner: full frame, no backdrop showing
    box = next(b for b in report.shots[0].boxes if b.role == "headline")
    lit = [
        (x, y)
        for x in range(int(box.x), int(box.x + box.width), 3)
        for y in range(int(box.y), int(box.y + box.height), 3)
        if sum(first.getpixel((x, y))) > 600
    ]
    assert len(lit) > 50  # the caption's white letters are already on screen in frame 0
    middle = frame(video, 3.2, tmp_path / "dissolve.png").getpixel((40, 960))
    assert middle[0] > 40 and middle[1] > 80  # red and green both show while one dissolves into the other
    last = frame(video, 5.9, tmp_path / "last.png")
    assert last.getpixel((540, 960))[1] > 120  # the green photo
    assert last.getpixel((540, 20)) == pytest.approx((255, 255, 255), abs=40)  # with its top band at the top
