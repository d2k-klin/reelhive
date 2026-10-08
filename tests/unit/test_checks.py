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
    for i, f in enumerate(brief.features, start=2):
        scenes.append(
            FeatureCardScene(index=i, narration=words(per_scene_words), feature=f, text=FeatureCardText(headline="F"))
        )
    closing = words(per_scene_words - len(brief.closing.split())) + " " + brief.closing
    scenes.append(CtaScene(index=len(scenes) + 1, narration=closing, text=CtaText(headline="Go")))
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
    spec.scenes[1].feature = None
    spec.scenes[0].text.headline = "x" * 60  # assignment skips validation, like a hand-edited spec
    checks = by_name(hard_checks(spec, brief, narrated))
    assert not checks["duration"].passed and "40.0s" in checks["duration"].message
    assert not checks["closing"].passed
    assert not checks["features"].passed and brief.features[0] in checks["features"].message
    assert not checks["text_limits"].passed
    assert not checks["audio"].passed and "[5]" in checks["audio"].message


def test_pace_bounds(brief):
    spec, narrated = good_spec(brief, per_scene_words=8)
    assert not by_name(hard_checks(spec, brief, narrated))["pace"].passed
