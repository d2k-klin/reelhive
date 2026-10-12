import pytest

from reelhive.nodes.timing_node import (
    FINAL_HOLD,
    FPS,
    LEAD,
    MAX_EXTRA,
    SHOT,
    apply_timing,
    available_seconds,
    beats_for,
    credit_for,
    place_urls,
    tail_for,
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
    assert spec.scenes[0].duration == pytest.approx(2.0 + LEAD + tail_for(brief) + MAX_EXTRA, abs=1 / FPS)
    assert spec.duration < brief.duration * 0.95


def test_long_speech_trims_tails_but_not_below_the_minimum(brief):
    spec = apply_timing(spec_with(6), narrated([12.0] * 6), brief)
    assert spec.scenes[0].duration == pytest.approx(12.0 + 0.3 + 0.3, abs=1 / FPS)


def test_credit_counts_toward_target_and_env_var_removes_it(brief, monkeypatch):
    with_credit = target_words(brief)
    monkeypatch.setenv("REELHIVE_DISABLE_CREDIT", "true")
    assert credit_for(brief) is None
    assert target_words(brief) > with_credit  # the credit's 1.5 s go back to the narration
    spec = apply_timing(spec_with(6), narrated([8.0] * 6), brief)
    assert spec.credit is None


def test_corner_credit_takes_no_time(brief):
    corner = brief.model_copy(update={"credit": "corner"})
    credit = credit_for(corner)
    assert credit and credit.mode == "corner" and credit.duration == 0


@pytest.mark.parametrize("duration", [15, 30, 60, 180])
def test_the_voice_plus_every_scenes_pause_fits_the_target(brief, duration):
    sized = brief.model_copy(update={"duration": duration})
    beats = beats_for(sized)
    speech = target_words(sized) / 161 * 60
    padding = beats * (LEAD + tail_for(sized)) + FINAL_HOLD
    assert speech + padding <= duration - INTRO_SECONDS - CREDIT_SECONDS + 0.2


@pytest.mark.parametrize("pacing", ["slow", "balanced", "fast"])
def test_one_beat_per_average_shot(brief, pacing):
    paced = brief.model_copy(update={"pacing": pacing})
    seconds = (60 - INTRO_SECONDS - CREDIT_SECONDS - FINAL_HOLD) / beats_for(paced)
    assert seconds == pytest.approx(SHOT[pacing][0], rel=0.15)  # the screen changes about every SHOT seconds
    assert beats_for(brief.model_copy(update={"duration": 180})) == round((180 - 5.5) / SHOT["balanced"][0])


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


def test_the_script_writer_must_write_about_one_beat_per_shot():
    from pydantic import ValidationError

    from reelhive.agents.script_writer import script_model

    model = script_model(12)
    beat = {"role": "feature", "narration": "One short idea."}
    assert len(model(title="t", beats=[beat] * 10).beats) == 10  # a couple fewer is fine
    with pytest.raises(ValidationError, match="at least 10"):
        model(title="t", beats=[beat] * 6)  # six long beats would hold each screen for ten seconds
    with pytest.raises(ValidationError, match="at most 14"):
        model(title="t", beats=[beat] * 15)
