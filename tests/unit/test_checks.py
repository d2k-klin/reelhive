from conftest import words

from reelhive.agents.critic import hard_checks
from reelhive.nodes.timing_node import apply_timing
from reelhive.schemas.scene_spec import (
    CtaScene,
    CtaText,
    FeatureCardScene,
    FeatureCardText,
    HookScene,
    HookText,
    SceneSpec,
)


def good_spec(brief, per_scene_words=28):
    scenes = [HookScene(index=1, narration=words(per_scene_words), text=HookText(headline="Hook"))]
    for i in range(2, len(brief.features) + 2):
        scenes.append(
            FeatureCardScene(
                index=i, narration=words(per_scene_words), covers=[i - 1], text=FeatureCardText(headline="F")
            )
        )
    scenes.append(CtaScene(index=len(scenes) + 1, narration=words(per_scene_words), text=CtaText(headline="Go")))
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
    spec.scenes[1].covers = []
    spec.scenes[0].text.headline = "x" * 60  # assignment skips validation, like a hand-edited spec
    checks = by_name(hard_checks(spec, brief, narrated))
    assert not checks["duration"].passed and "40.0s" in checks["duration"].message
    assert "closing" not in checks  # the closing is an idea the writers polish; the critic judges it
    assert not checks["features"].passed and brief.features[0] in checks["features"].message
    assert not checks["text_limits"].passed
    assert not checks["audio"].passed and "[5]" in checks["audio"].message


def test_pace_bounds(brief):
    spec, narrated = good_spec(brief, per_scene_words=8)
    assert not by_name(hard_checks(spec, brief, narrated))["pace"].passed


def test_pace_floor_follows_a_slow_voice(brief):
    spec, narrated = good_spec(brief)
    slow = {i: (text, len(text.split()) / 2.0) for i, (text, _) in narrated.items()}  # 120 wpm voice
    spec = apply_timing(spec, slow, brief)
    pace = by_name(hard_checks(spec, brief, slow))["pace"]
    assert pace.passed and pace.threshold.startswith("102-")
