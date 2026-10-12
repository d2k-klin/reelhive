"""The sound designer: only reported moments, only suitable effects, few of them, never on the voice."""

import numpy as np
import pytest
import soundfile as sf
from pydantic import ValidationError

from reelhive.agents.sound_designer import (
    MAX_CUES,
    Opening,
    budget,
    nearest_word,
    openings,
    plan_model,
    spoken,
)
from reelhive.audio import mixer
from reelhive.audio.sfx_library import SFX_DIR, load_effects
from reelhive.config import REPO_ROOT
from reelhive.schemas.layout import LayoutReport, Moment, ShotLayout
from reelhive.schemas.scene_spec import HookScene, HookText, SceneSpec, SoundCue, Word

EFFECTS = load_effects()
WORDS = [(1.0, 1.4), (1.5, 2.0), (10.3, 10.8)]
MOMENTS = [
    Opening("scene 1 cut", "cut", 0.0, "open", "scene 1"),
    Opening("scene 1 arrive", "arrive", 0.8, "hook", "scene 1"),
    Opening("scene 2 cut", "cut", 4.0, "push", "scene 2"),
    Opening("scene 2 focus", "focus", 1.7, "Pricing table", "scene 2"),
    Opening("scene 3 cut", "cut", 10.0, "carry", "scene 3"),
    Opening("scene 4 arrive", "arrive", 18.0, "cta", "scene 4"),
]


def plan(*cues, duration=20.0):
    model = plan_model(MOMENTS, EFFECTS, duration, WORDS)
    return model(cues=[{"moment": m, "effect": e, "gain_db": g, "reason": "r"} for m, e, g in cues], reason="r")


def test_the_budget_is_one_per_started_half_minute_and_capped():
    assert [budget(d) for d in (15, 29, 30, 60, 180)] == [1, 1, 2, 3, MAX_CUES]


def test_no_effects_is_a_valid_plan():
    assert plan(duration=20).cues == []


def test_a_good_plan_passes():
    out = plan(("scene 2 cut", "whoosh-soft", -18), ("scene 4 arrive", "chime-bright", -16), duration=40)
    assert [c.moment for c in out.cues] == ["scene 2 cut", "scene 4 arrive"]


@pytest.mark.parametrize(
    ("cues", "duration", "problem"),
    [
        ([("scene 2 cut", "whoosh-soft", -18), ("scene 4 arrive", "chime-bright", -18)], 20, "at most 1"),
        ([("scene 2 cut", "click-ui", -18)], 20, "does not suit a cut"),
        ([("scene 1 cut", "whoosh-soft", -18)], 20, "outside the video"),
        ([("scene 2 focus", "click-ui", -20)], 20, "lands on a spoken word"),
        ([("scene 3 cut", "whoosh-soft", -14)], 20, "plays under the voice"),
        ([("scene 1 arrive", "pop-soft", -18), ("scene 2 cut", "whoosh-soft", -18)], 40, "keep 5s"),
        ([("scene 9 cut", "whoosh-soft", -18)], 20, "scene 9 cut"),
        ([("scene 2 cut", "airhorn", -18)], 20, "airhorn"),
        ([("scene 2 cut", "whoosh-soft", -3)], 20, "less than or equal to -10"),
    ],
)
def test_rules_reach_the_model_as_validation_errors(cues, duration, problem):
    with pytest.raises(ValidationError, match=problem):
        plan(*cues, duration=duration)


def test_moments_come_from_the_layout_report_in_time_order():
    report = LayoutReport(
        shots=[
            ShotLayout(kind="scene", index=2, width=1, height=1, moments=[Moment(kind="cut", at=5.0, detail="push")]),
            ShotLayout(
                kind="intro", index=0, width=1, height=1, moments=[Moment(kind="arrive", at=1.2, detail="intro")]
            ),
        ]
    )
    assert [(o.id, o.at) for o in openings(report)] == [("intro arrive", 1.2), ("scene 2 cut", 5.0)]


def test_spoken_words_are_on_the_video_clock():
    scene = HookScene(
        index=1, narration="Go", text=HookText(headline="h"), start=3.0, words=[Word(text="Go", start=0.3, end=0.6)]
    )
    words = spoken(SceneSpec(scenes=[scene]))
    assert words == [(3.3, 3.6)] and nearest_word(3.4, words) == 0 and nearest_word(4.6, words) == pytest.approx(1.0)


def test_the_library_is_48khz_and_its_manifest_matches_the_files():
    for effect in EFFECTS:
        audio, rate = sf.read(SFX_DIR / effect["file"])
        assert rate == mixer.EFFECTS_RATE and len(audio) / rate == pytest.approx(effect["duration"], abs=0.002)
        assert 0 <= effect["peak"] < effect["duration"] and set(effect["suits"]) <= {"cut", "arrive", "focus"}


def test_moment_kinds_match_the_renderer():
    import re
    from typing import get_args

    measure = (REPO_ROOT / "renderer/src/measure.ts").read_text()
    kinds = re.search(r"kind: ('[a-z]+'(?: \| '[a-z]+')*);", measure)
    assert kinds and set(re.findall(r"'([a-z]+)'", kinds[1])) == set(get_args(Moment.model_fields["kind"].annotation))


def test_effects_are_placed_at_their_level_on_one_track(tmp_path):
    spec = SceneSpec(
        duration=3.0,
        scenes=[HookScene(index=1, narration="", text=HookText(headline="h"))],
        sound_effects=[SoundCue(effect="pop-soft.wav", moment="scene 1 arrive", at=1.0, gain_db=-20)],
    )
    track, rate = sf.read(mixer.effects_track(spec, tmp_path / "effects.wav"))
    assert rate == mixer.EFFECTS_RATE and len(track) == 3 * rate
    assert np.abs(track[: rate - 10]).max() == 0  # silent before the cue
    pop, _ = sf.read(SFX_DIR / "pop-soft.wav")
    assert np.abs(track).max() == pytest.approx(np.abs(pop).max() * 10 ** (-20 / 20), rel=0.01)


def test_mix_adds_the_effects_track_alongside_voice_and_music(tmp_path):
    args = mixer.mix_args(
        tmp_path / "n.wav", tmp_path / "m.mp3", 30.0, tmp_path / "mix.wav", effects=tmp_path / "e.wav"
    )
    graph = args[args.index("-filter_complex") + 1]
    assert "[ducked][voice][effects]amix=inputs=3" in graph and "[2:a]" in graph
    alone = mixer.mix_args(tmp_path / "n.wav", None, 30.0, tmp_path / "mix.wav", effects=tmp_path / "e.wav")
    assert "[voice][effects]amix=inputs=2" in alone[alone.index("-filter_complex") + 1]


def test_an_effect_on_a_word_is_allowed_only_very_quietly():
    assert plan(("scene 2 focus", "click-ui", -26), duration=20).cues[0].gain_db == -26
