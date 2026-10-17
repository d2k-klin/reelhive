"""Real Revideo: a Reel with every text and image template, its longest copy and captions on, laid out clear of the
app's buttons and readable on its very first frame."""

import subprocess

import pytest
from PIL import Image

from reelhive.agents.reviewer import layout_checks
from reelhive.audio.mixer import ffmpeg_exe
from reelhive.render.bridge import layout_path, render
from reelhive.schemas.layout import LayoutReport
from reelhive.schemas.scene_spec import (
    PLATFORM_SAFE_AREAS,
    BulletsScene,
    BulletsText,
    Credit,
    CtaScene,
    CtaText,
    FeatureCardScene,
    FeatureCardText,
    HookScene,
    HookText,
    ImageScene,
    Intro,
    Motion,
    OfferScene,
    OfferText,
    ProblemScene,
    ReviewScene,
    ReviewText,
    SceneSpec,
    StatScene,
    StatText,
    VisualAsset,
    Word,
)

pytestmark = pytest.mark.slow

HEADLINE = "Every cloud bill, explained before it lands"  # 44 of 48
SUBLINE = "Find the idle servers, orphaned disks and forgotten test clusters"  # 66 of 80


def timed(text: str, start: float = 0.3) -> list[Word]:
    return [Word(text=w, start=start + i * 0.3, end=start + i * 0.3 + 0.25) for i, w in enumerate(text.split()[:6])]


def reel(tmp_path) -> SceneSpec:
    Image.new("RGB", (1600, 1600), "#3b6ea8").save(tmp_path / "product.png")
    scenes = [
        HookScene(index=1, narration=HEADLINE, text=HookText(headline=HEADLINE, subline=SUBLINE)),
        ProblemScene(index=2, narration="x", text=HookText(headline=HEADLINE, subline=SUBLINE)),
        FeatureCardScene(
            index=3,
            narration="x",
            text=FeatureCardText(label="01", headline="Every cost, owned by a team", body=SUBLINE + " today"),
        ),
        StatScene(index=4, narration="x", text=StatText(headline="~30% wasted", subline=SUBLINE)),
        BulletsScene(
            index=5,
            narration="x",
            text=BulletsText(
                headline="What CostHive finds for you", items=[SUBLINE, "Idle databases", "Unused IPs", "Old snapshots"]
            ),
        ),
        ImageScene(
            index=6,
            narration="x",
            text=HookText(headline=HEADLINE, subline=SUBLINE),
            visual=VisualAsset(source="provided", file="product.png"),
        ),
        OfferScene(
            index=7,
            narration="x",
            text=OfferText(
                headline="CostHive Pro, every region", price="$1,249.99", was="$1,499", subline=SUBLINE[:60]
            ),
        ),
        ReviewScene(
            index=8,
            narration="x",
            text=ReviewText(
                headline=(SUBLINE + " in an afternoon, and paid for itself")[:120], subline="Priya, SRE", rating=4.5
            ),
        ),
        CtaScene(
            index=9,
            narration="x",
            text=CtaText(headline="Try CostHive free and cut the waste this week", url="costhive.dev"),
        ),
    ]
    start = 0.0
    for scene in scenes:
        scene.start, scene.duration, scene.words = start, 2.0, timed(HEADLINE)
        start += 2.0 + (1.5 if scene.index == 1 else 0)
    return SceneSpec(
        format="9:16",
        width=1080,
        height=1920,
        duration=start + 1.5,
        motion=Motion(enter=0.5, transition=0.4, open=0.0),
        safe_area=PLATFORM_SAFE_AREAS["reels"],
        captions=True,
        intro=Intro(title="CostHive", tagline="Cloud bills, explained", url="costhive.dev", duration=1.5),
        intro_at=1,
        scenes=scenes,
        credit=Credit(mode="end", duration=1.5),
    )


def test_a_reel_stays_clear_of_the_apps_buttons_and_opens_readable(tmp_path):
    spec = reel(tmp_path)
    path = tmp_path / "spec.json"
    path.write_text(spec.model_dump_json())
    output = tmp_path / "video.mp4"
    render(path, output, lambda _: None)
    report = LayoutReport.model_validate_json(layout_path(output).read_text())
    failed = {c.name: c.message for c in layout_checks(report, spec) if not c.passed}
    assert not failed

    first = tmp_path / "first.png"
    subprocess.run([ffmpeg_exe(), "-v", "error", "-i", str(output), "-frames:v", "1", str(first)], check=True)
    with Image.open(first) as frame:
        top, bottom = int(1920 * 0.13), int(1920 * 0.78)
        lit = sum(1 for y in range(top, bottom, 4) for x in range(0, 1080, 4) if sum(frame.getpixel((x, y))) > 600)
    assert lit > 200  # the hook's headline is already on screen in frame 0
