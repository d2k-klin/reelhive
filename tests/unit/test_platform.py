"""A brief made for Reels, Shorts or TikTok: its defaults, its timing, and the safe area the review holds it to."""

import pytest

from reelhive.agents.critic import hard_checks
from reelhive.agents.reviewer import layout_checks
from reelhive.nodes.timing_node import PLATFORM_INTRO, PUNCHY_MOTION, SHOT, apply_timing, beats_for, target_words
from reelhive.schemas.brief import Brief
from reelhive.schemas.layout import Box, LayoutReport, ShotLayout
from reelhive.schemas.scene_spec import PLATFORM_SAFE_AREAS, HookScene, HookText, Intro, Motion, SafeArea, SceneSpec


def social(brief: Brief, **extra) -> Brief:
    """The example brief made for Reels, leaving the platform's own settings to it."""
    own = brief.model_dump(exclude_unset=True, exclude={"format", "pacing", "captions", "cold_open"})
    return Brief.model_validate({**own, "platform": "reels", **extra})


def test_a_platform_brings_its_defaults_and_the_brief_still_wins(brief):
    reel = social(brief)
    assert (reel.format, reel.pacing, reel.captions, reel.cold_open) == ("9:16", "punchy", True, True)
    assert social(brief, pacing="fast", captions=False).pacing == "fast"
    assert not social(brief, captions=False).captions
    assert Brief.model_validate(brief.model_dump(exclude_unset=True)).pacing == "balanced"  # no platform, no change


def test_a_platform_cut_opens_settled_on_a_short_intro_inside_the_apps_safe_area(brief):
    spec = SceneSpec(
        intro=Intro(title="CostHive"),
        intro_at=1,
        scenes=[HookScene(index=1, narration="s1", text=HookText(headline="h"))],
    )
    apply_timing(spec, {1: ("s1", 2.0)}, social(brief))
    assert spec.intro and spec.intro.duration == PLATFORM_INTRO
    assert spec.motion == PUNCHY_MOTION.model_copy(update={"open": 0.0})
    assert spec.safe_area == PLATFORM_SAFE_AREAS["reels"]
    apply_timing(spec, {1: ("s1", 2.0)}, social(brief, format="1:1"))  # letterboxed: the buttons sit on the bars
    assert spec.safe_area == SafeArea()
    apply_timing(spec, {1: ("s1", 2.0)}, brief)
    assert (spec.safe_area, spec.motion, spec.intro.duration) == (SafeArea(), Motion(), 3.0)


@pytest.mark.parametrize("duration", [15, 30, 60, 90])
@pytest.mark.parametrize("voice_wpm", [145, 161])  # Kokoro on product copy, and on plain text
def test_a_punchy_script_at_its_word_target_passes_the_hard_checks(brief, duration, voice_wpm):
    reel = social(brief, duration=duration)
    beats, total = beats_for(reel), target_words(reel)
    counts = [total // beats + (i < total % beats) for i in range(beats)]  # the target, spread over the beats
    scenes = [
        HookScene(index=i, narration=" ".join(["word"] * n), text=HookText(headline="Short line"))
        for i, n in enumerate(counts, start=1)
    ]
    scenes[0].covers = list(range(1, len(reel.features) + 1))
    spec = SceneSpec(format="9:16", width=1080, height=1920, intro=Intro(title="CostHive"), intro_at=1, scenes=scenes)
    narrated = {s.index: (s.narration, n / voice_wpm * 60) for s, n in zip(scenes, counts, strict=True)}
    apply_timing(spec, narrated, reel)
    failed = {c.name: c.message for c in hard_checks(spec, reel, narrated) if not c.passed}
    assert not failed
    assert sum(s.duration for s in scenes) / beats <= SHOT["punchy"][0] * 1.25


def test_the_review_keeps_text_clear_of_the_apps_buttons(brief):
    caption_zone = Box(role="headline", x=200, y=1600, width=600, height=100, font_size=70)  # over the app's caption
    report = LayoutReport(shots=[ShotLayout(kind="scene", index=1, width=1080, height=1920, boxes=[caption_zone])])
    spec = SceneSpec(scenes=[HookScene(index=1, narration="s1", text=HookText(headline="h"))])
    assert all(c.passed for c in layout_checks(report, spec))  # fine on a plain 9:16
    spec.safe_area = PLATFORM_SAFE_AREAS["reels"]
    failed = [c for c in layout_checks(report, spec) if not c.passed]
    assert [c.name for c in failed] == ["safe_area"] and "bottom 22%" in failed[0].threshold
