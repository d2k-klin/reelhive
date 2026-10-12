from conftest import beat_notes, words

from reelhive.agents.critic import hard_checks
from reelhive.nodes.timing_node import apply_timing, target_words
from reelhive.schemas.scene_spec import (
    CtaScene,
    CtaText,
    FeatureCardScene,
    FeatureCardText,
    HookScene,
    HookText,
    SceneSpec,
)


def good_spec(brief, per_scene_words=None):
    """One scene per beat the video needs (hook, notes, more feature beats, call to action), voiced at 2.6 words/s."""
    notes = beat_notes(brief)
    per = per_scene_words or -(-target_words(brief) // len(notes))
    scenes = []
    for i, (role, note) in enumerate(notes, start=1):
        if role == "cta":
            scenes.append(CtaScene(index=i, narration=words(per), text=CtaText(headline="Go")))
        elif role == "feature":
            scenes.append(
                FeatureCardScene(
                    index=i, narration=words(per), covers=[note] if note else [], text=FeatureCardText(headline="F")
                )
            )
        else:
            scenes.append(HookScene(index=i, narration=words(per), text=HookText(headline="Hook")))
    spec = SceneSpec(scenes=scenes)
    narrated = {s.index: (s.narration, len(s.narration.split()) / 2.6) for s in spec.scenes}
    return apply_timing(spec, narrated, brief), narrated


def by_name(checks):
    return {c.name: c for c in checks}


def test_good_spec_passes_every_check(brief):
    spec, narrated = good_spec(brief)
    failed = [c for c in hard_checks(spec, brief, narrated) if not c.passed]
    assert failed == []


def test_each_check_can_fail(brief):
    spec, narrated = good_spec(brief)
    spec.duration = 40.0
    spec.scenes[-1].narration = "Something else entirely."
    spec.scenes[-1].text.headline = "Different"
    next(s for s in spec.scenes if 1 in s.covers).covers = []
    spec.scenes[0].text.headline = "x" * 60  # assignment skips validation, like a hand-edited spec
    checks = by_name(hard_checks(spec, brief, narrated))
    assert not checks["duration"].passed and "40.0s" in checks["duration"].message
    assert "closing" not in checks  # the closing is an idea the writers polish; the critic judges it
    assert not checks["features"].passed and brief.features[0] in checks["features"].message
    assert not checks["text_limits"].passed
    assert not checks["audio"].passed and f"[{len(spec.scenes)}]" in checks["audio"].message


def test_pace_bounds(brief):
    spec, narrated = good_spec(brief, per_scene_words=8)
    assert not by_name(hard_checks(spec, brief, narrated))["pace"].passed


def test_pace_floor_follows_a_slow_voice(brief):
    spec, narrated = good_spec(brief)
    slow = {i: (text, len(text.split()) / 2.0) for i, (text, _) in narrated.items()}  # 120 wpm voice
    spec = apply_timing(spec, slow, brief)
    pace = by_name(hard_checks(spec, brief, slow))["pace"]
    assert pace.passed and pace.threshold.startswith("102-")


def test_a_screen_held_too_long_fails_the_shot_length_check(brief):
    spec, narrated = good_spec(brief)
    assert by_name(hard_checks(spec, brief, narrated))["shot_length"].passed
    long = spec.scenes[2]
    long.duration = 9.0  # one scene lingers
    check = by_name(hard_checks(spec, brief, narrated))["shot_length"]
    assert not check.passed and f"scene {long.index}: 9.0s" in check.message
    long.duration_override = 9.0  # unless the user set that length themselves
    assert by_name(hard_checks(spec, brief, narrated))["shot_length"].passed


def test_few_long_beats_fail_on_the_average_even_under_the_longest(brief):
    spec, narrated = good_spec(brief)
    for scene in spec.scenes:
        scene.duration = 6.5  # each under 7 s, but far over a 4.5 s average
    check = by_name(hard_checks(spec, brief, narrated))["shot_length"]
    assert not check.passed and "on average" in check.message
