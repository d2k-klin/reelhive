import pytest
from pydantic import ValidationError

from reelhive.agents.plan import PlannedScene
from reelhive.schemas.brief import Brief


def test_example_brief_is_valid(brief):
    assert brief.level == "low"
    assert Brief.model_validate({**brief.model_dump(), "level": "small"}).level == "low"  # legacy alias
    assert brief.voice.gender == "female"
    assert brief.credit == "end"


@pytest.mark.parametrize(
    "change, message",
    [
        ({"features": []}, "at least 1"),
        ({"features": [f"f{i}" for i in range(9)]}, "at most 8"),
        ({"duration": 5}, "greater than or equal to 15"),
        ({"visuals": {"url": "file:///etc/passwd"}}, "http"),
    ],
)
def test_brief_rejects(brief, change, message):
    with pytest.raises(ValidationError, match=message):
        Brief.model_validate({**brief.model_dump(), **change})


def test_planned_scene_enforces_template_limits():
    with pytest.raises(ValidationError, match="does not fit the feature-card template"):
        PlannedScene(template="feature-card", headline="x" * 41)
    PlannedScene(template="cta", headline="x" * 60)  # cta allows longer headlines


def test_high_brief_is_available_in_m3(brief):
    assert Brief.model_validate({**brief.model_dump(), "level": "high"}).level == "high"


def test_planned_scene_maps_secondary_to_template_field():
    card = PlannedScene(
        template="feature-card", headline="Scans", secondary="Every region", label="01", covers=[2]
    ).to_scene(3, "spoken")
    assert card.text.model_dump() == {"label": "01", "headline": "Scans", "body": "Every region"}
    assert (card.index, card.narration, card.covers) == (3, "spoken", [2])
    hook = PlannedScene(template="hook", headline="Hi", secondary="there").to_scene(1, "x")
    assert hook.text.model_dump() == {"headline": "Hi", "subline": "there"}
