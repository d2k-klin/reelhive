"""Real Revideo: portrait/square visuals, brand, frames and wrapped copy."""

import subprocess

import pytest
from PIL import Image, ImageDraw

from reelhive.audio.mixer import ffmpeg_exe, probe
from reelhive.render.bridge import render
from reelhive.schemas.scene_spec import (
    Credit,
    CtaScene,
    CtaText,
    FeatureCardScene,
    FeatureCardText,
    HookText,
    SceneSpec,
    ScreenshotScene,
    Theme,
    VisualAsset,
)

pytestmark = pytest.mark.slow


@pytest.mark.parametrize("format,size,frame", [("9:16", (1080, 1920), "phone"), ("1:1", (1080, 1080), "browser")])
def test_visual_format_renders(tmp_path, format, size, frame):
    image = Image.new("RGB", (1080, 2200), "#e94343")
    draw = ImageDraw.Draw(image)
    draw.rectangle((100, 200, 980, 450), fill="#ffffff")
    draw.rectangle((100, 1800, 980, 2050), fill="#3030ff")
    image.save(tmp_path / "screenshot.png")
    image.resize((100, 100)).save(tmp_path / "logo.png")
    spec = SceneSpec(
        format=format,
        width=size[0],
        height=size[1],
        duration=6,
        theme=Theme(accent="#44dd88", logo="logo.png"),
        credit=Credit(mode="end", duration=1.5),
        scenes=[
            ScreenshotScene(
                index=1,
                narration="",
                duration=1.5,
                text=HookText(headline="See your whole dashboard", subline="Real screenshots, private by default"),
                visual=VisualAsset(source="screenshot", file="screenshot.png", frame=frame),
            ),
            FeatureCardScene(
                index=2,
                narration="",
                start=1.5,
                duration=1.5,
                text=FeatureCardText(
                    headline="Every feature in one place",
                    body="Clear narration and a brand theme that works in portrait and square formats.",
                ),
            ),
            CtaScene(
                index=3,
                narration="",
                start=3,
                duration=1.5,
                text=CtaText(headline="Try ReelHive today.", subline="https://example.com/your-product/get-started"),
            ),
        ],
    )
    path = tmp_path / "spec.json"
    path.write_text(spec.model_dump_json())
    output = tmp_path / "video.mp4"
    render(path, output, lambda _: None)
    info = probe(output)
    assert (info["width"], info["height"]) == size
    assert info["duration"] == pytest.approx(6, abs=0.2)
    still = tmp_path / "preview.png"
    subprocess.run(
        [ffmpeg_exe(), "-v", "error", "-ss", "0.75", "-i", str(output), "-frames:v", "1", str(still)], check=True
    )
    with Image.open(still) as rendered:
        assert rendered.getpixel((size[0] // 2, size[1] // 2))[0] > 150  # screenshot reached the video

    # During the fully visible hold, tall screenshots must actually travel.
    from PIL import ImageChops

    frames = []
    for stamp in (0.55, 1.0):
        still = tmp_path / f"pan-{stamp}.png"
        subprocess.run(
            [ffmpeg_exe(), "-v", "error", "-ss", str(stamp), "-i", str(output), "-frames:v", "1", str(still)],
            check=True,
        )
        with Image.open(still) as image:
            frames.append(image.crop((size[0] * 0.2, size[1] * 0.2, size[0] * 0.8, size[1] * 0.65)))
    assert ImageChops.difference(*frames).getbbox() is not None
