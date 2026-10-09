import pytest

from reelhive.nodes.timing_node import (
    FPS,
    MAX_EXTRA,
    apply_timing,
    available_seconds,
    credit_for,
    place_urls,
    target_words,
)
from reelhive.schemas.scene_spec import (
    CREDIT_SECONDS,
    INTRO_SECONDS,
    CtaScene,
    CtaText,
    HookScene,
    HookText,
    Intro,
    SceneSpec,
    display_url,
)


def spec_with(n: int) -> SceneSpec:
    return SceneSpec(
        scenes=[HookScene(index=i, narration=f"s{i}", text=HookText(headline="h")) for i in range(1, n + 1)]
    )


def narrated(seconds: list[float]) -> dict[int, tuple[str, float]]:
    return {i: (f"s{i}", s) for i, s in enumerate(seconds, start=1)}


def test_pads_short_speech_to_hit_the_target(brief):
    spec = apply_timing(spec_with(6), narrated([8.0] * 6), brief)
    assert spec.duration == pytest.approx(brief.duration, abs=0.1)
    assert spec.credit and spec.credit.duration == CREDIT_SECONDS
    assert [s.start for s in spec.scenes] == sorted(s.start for s in spec.scenes)
    assert all(s.audio == f"audio/scene_{s.index:02d}.wav" for s in spec.scenes)
    assert all(abs(s.duration * FPS - round(s.duration * FPS)) < 0.01 for s in spec.scenes)  # whole frames


def test_padding_is_capped_so_the_duration_check_can_catch_thin_scripts(brief):
    spec = apply_timing(spec_with(3), narrated([2.0] * 3), brief)
    assert spec.scenes[0].duration == pytest.approx(2.0 + 0.3 + 0.7 + MAX_EXTRA, abs=1 / FPS)
    assert spec.duration < brief.duration * 0.95


def test_long_speech_trims_tails_but_not_below_the_minimum(brief):
    spec = apply_timing(spec_with(6), narrated([12.0] * 6), brief)
    assert spec.scenes[0].duration == pytest.approx(12.0 + 0.3 + 0.3, abs=1 / FPS)


def test_credit_counts_toward_target_and_env_var_removes_it(brief, monkeypatch):
    assert target_words(brief) == round((60 - INTRO_SECONDS - CREDIT_SECONDS) * 145 / 60)
    monkeypatch.setenv("REELHIVE_DISABLE_CREDIT", "true")
    assert credit_for(brief) is None
    assert target_words(brief) == round((60 - INTRO_SECONDS) * 145 / 60)
    spec = apply_timing(spec_with(6), narrated([8.0] * 6), brief)
    assert spec.credit is None


def test_corner_credit_takes_no_time(brief):
    corner = brief.model_copy(update={"credit": "corner"})
    credit = credit_for(corner)
    assert credit and credit.mode == "corner" and credit.duration == 0


def test_short_videos_leave_room_for_scene_padding(brief):
    short = brief.model_copy(update={"duration": 15})  # 3 features -> 6 scenes in 10.5s
    words = target_words(short)
    speech = words / 161 * 60
    assert speech + 6 * (0.3 + 0.3) <= 10.5 + 0.2  # voice plus minimum padding fits
    assert target_words(brief) == round((60 - INTRO_SECONDS - CREDIT_SECONDS) * 145 / 60)  # long videos are unchanged


def test_intro_opens_the_video_and_counts_toward_the_target(brief):
    spec = spec_with(6)
    spec.intro = Intro(title="ScanComb", tagline="Next-level platform for IT security and compliance")
    spec = apply_timing(spec, narrated([8.0] * 6), brief)
    assert spec.scenes[0].start == INTRO_SECONDS  # the voice starts after the title screen
    assert spec.duration == pytest.approx(brief.duration, abs=0.1)
    assert available_seconds(brief) == brief.duration - INTRO_SECONDS - CREDIT_SECONDS


def test_a_spec_without_an_intro_keeps_its_timing(brief):
    spec = apply_timing(spec_with(6), narrated([8.0] * 6), brief)
    assert spec.scenes[0].start == 0
    assert spec.duration == pytest.approx(brief.duration, abs=0.1)


@pytest.mark.parametrize(
    ("raw", "shown"),
    [
        ("https://www.ScanComb.com/", "scancomb.com"),
        ("scancomb.com/en/product/?ref=ad#top", "scancomb.com/en/product"),
        ("example.com", "example.com"),
        ("https://" + "a" * 50 + ".com/" + "b" * 20, "a" * 50 + ".com"),  # a path that does not fit is dropped
        ("", None),
        (None, None),
    ],
)
def test_display_url_is_how_people_say_an_address(raw, shown):
    assert display_url(raw) == shown


def test_site_address_is_placed_by_code_and_never_overwritten(brief):
    closing = CtaScene(index=2, narration="x", text=CtaText(headline="Go"))
    spec = SceneSpec(
        intro=Intro(title="Example"), scenes=[HookScene(index=1, narration="x", text=HookText(headline="h")), closing]
    )
    both = brief.model_copy(update={"website": "https://www.Example.com/", "cta_url": "example.com/go"})
    place_urls(spec, both)
    assert spec.intro and spec.intro.url == "example.com"  # the product site on the intro
    assert closing.text.url == "example.com/go"  # the call-to-action address on the closing scene
    closing.text.url = "mine.dev"
    place_urls(spec, both)
    assert closing.text.url == "mine.dev"
    bare = SceneSpec(intro=Intro(title="Example"), scenes=[closing.model_copy(update={"text": CtaText(headline="Go")})])
    place_urls(bare, brief)  # the fixture brief gives no address
    assert bare.intro and bare.intro.url is None and bare.scenes[0].text.url is None  # type: ignore[union-attr]
