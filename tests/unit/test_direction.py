"""Shot direction: holds, the cold open, pacing, reading time, focus regions, layout gates and loop routing."""

from types import SimpleNamespace

import pytest
from PIL import Image

from reelhive.agents.critic import hard_checks
from reelhive.agents.plan import PlannedScene, intro_position, keep_direction
from reelhive.agents.reviewer import MAX_REVIEW_ROUNDS, MAX_ZOOM, MIN_TYPE, layout_checks
from reelhive.core.context import RunContext
from reelhive.core.events import EventBus
from reelhive.graphs.production import critic_failed, critic_passed, review_failed
from reelhive.nodes.timing_node import FINAL_HOLD, LEAD, PACE, apply_timing, tail_for, target_words
from reelhive.schemas.layout import Box, LayoutReport, ShotLayout
from reelhive.schemas.scene_spec import (
    HookScene,
    HookText,
    Intro,
    SceneSpec,
    ScreenshotScene,
    VisualRequest,
)
from reelhive.visuals.resolver import focus_for


def hooks(n: int, **extra) -> list[HookScene]:
    return [
        HookScene(index=i, narration=f"s{i}", text=HookText(headline="Short line"), **extra) for i in range(1, n + 1)
    ]


def test_holds_and_the_settled_ending_add_still_time_after_the_voice(brief):
    brief.duration = 60
    spec = SceneSpec(scenes=hooks(3))
    spec.scenes[1].hold = 2.0
    apply_timing(spec, {i: (f"s{i}", 3.0) for i in (1, 2, 3)}, brief)
    base = 3.0 + LEAD + tail_for(brief)
    first, second, last = (s.duration for s in spec.scenes)
    assert second - first == pytest.approx(2.0, abs=1 / 30)
    assert last - first == pytest.approx(FINAL_HOLD, abs=1 / 30)
    assert first >= base


def test_the_intro_plays_after_the_hook_when_the_spec_says_so(brief):
    spec = SceneSpec(intro=Intro(title="CostHive"), intro_at=1, scenes=hooks(3))
    apply_timing(spec, {i: (f"s{i}", 2.0) for i in (1, 2, 3)}, brief)
    one, two, _ = spec.scenes
    assert one.start == 0 and two.start == pytest.approx(one.duration + 3.0, abs=1 / 30)
    assert [type(i).__name__ for i in spec.timeline()] == ["HookScene", "Intro", "HookScene", "HookScene"]
    with pytest.raises(ValueError, match="intro_at"):
        SceneSpec(intro=Intro(title="x"), intro_at=4, scenes=hooks(3))


def test_the_intro_opens_the_video_unless_the_brief_asks_for_a_cold_open():
    assert intro_position(hooks(2)) == 0  # the product is named first
    assert intro_position(hooks(2), cold_open=True) == 1  # a hook first, then the title screen
    shot = ScreenshotScene(index=1, narration="x", text=HookText(headline="h"))
    assert intro_position([shot], cold_open=True) == 0  # only a hook or problem plays before the intro


def test_pacing_sets_how_much_narration_the_script_gets(brief):
    words = {p: target_words(brief.model_copy(update={"pacing": p})) for p in PACE}
    assert words["slow"] < words["balanced"] < words["fast"]


def test_reading_time_fails_a_scene_with_more_words_than_its_screen_time(brief):
    spec = SceneSpec(scenes=hooks(1))
    spec.scenes[0].text = HookText(
        headline="Eight words that a viewer has to read", subline="and another ten words below it for good measure here"
    )
    spec.scenes[0].duration = 3.0
    check = next(c for c in hard_checks(spec, brief, {1: ("s1", 2.0)}) if c.name == "reading_time")
    assert not check.passed and "scene 1: 18 words" in check.message
    spec.scenes[0].duration = 6.0
    assert next(c for c in hard_checks(spec, brief, {1: ("s1", 2.0)}) if c.name == "reading_time").passed


def test_a_repair_keeps_the_direction_it_does_not_mention():
    prior = ScreenshotScene(index=1, narration="x", text=HookText(headline="h"), layout="split-left", hold=1.5)
    prior.visual_request = VisualRequest(kind="product_ui", route="/", region="r2")
    planned = PlannedScene(template="screenshot-pan", headline="Shorter")
    scene = planned.to_scene(1, "x")
    keep_direction(planned, scene, prior)
    assert (scene.layout, scene.hold, scene.visual_request.region) == ("split-left", 1.5, "r2")
    planned = PlannedScene(template="screenshot-pan", headline="h", layout="center", hold=0)
    scene = planned.to_scene(1, "x")
    keep_direction(planned, scene, prior)
    assert (scene.layout, scene.hold) == ("center", 0)


def test_a_planned_region_is_found_again_in_the_measured_capture(tmp_path, brief):
    image = tmp_path / "shot.png"
    Image.new("RGB", (1000, 2000)).save(image)
    ctx = RunContext(tmp_path, brief, EventBus(), {}, None, None)
    ctx.visual_catalog = [{"route": "https://x.test/", "regions": [{"id": "r2", "label": "section: Pricing"}]}]
    measured = [
        {"label": "form: Sign up", "box": [0, 0, 500, 300]},
        {"label": "section: Pricing", "box": [100, 1200, 800, 400]},
    ]
    focus = focus_for(ctx, "https://x.test/", "r2", measured, image)
    assert focus and (focus.x, focus.y, focus.width, focus.height) == (0.1, 0.6, 0.8, 0.2)
    assert focus.label == "section: Pricing"
    assert focus_for(ctx, "https://x.test/", "r9", measured, image) is None
    assert focus_for(ctx, "https://x.test/", None, measured, image) is None


def shot(*boxes: Box, zoom: float = 1.0) -> ShotLayout:
    return ShotLayout(kind="scene", index=1, width=1920, height=1080, boxes=list(boxes), zoom=zoom)


def failing(report: LayoutReport, spec: SceneSpec) -> set[str]:
    return {c.name for c in layout_checks(report, spec) if not c.passed}


def test_layout_gates_catch_clipped_colliding_tiny_and_blurry_elements():
    spec = SceneSpec(scenes=hooks(1))
    clean = Box(role="headline", x=400, y=400, width=1100, height=100, font_size=80)
    assert failing(LayoutReport(shots=[shot(clean)]), spec) == set()
    clipped = Box(role="subline", x=10, y=600, width=500, height=40, font_size=40)
    assert failing(LayoutReport(shots=[shot(clean, clipped)]), spec) == {"safe_area"}
    covering = Box(role="visual", x=500, y=380, width=600, height=400)
    assert failing(LayoutReport(shots=[shot(clean, covering)]), spec) == {"overlap"}
    tiny = Box(role="label", x=400, y=700, width=200, height=20, font_size=MIN_TYPE * 1080 - 2)
    assert failing(LayoutReport(shots=[shot(clean, tiny)]), spec) == {"type_size"}
    assert failing(LayoutReport(shots=[shot(clean, zoom=MAX_ZOOM + 0.1)]), spec) == {"sharpness"}
    assert failing(LayoutReport(), spec) == {"measured"}


def test_the_layout_report_keeps_the_last_measurement_of_each_shot():
    line = 'Worker 0: JSHandle:REELHIVE_LAYOUT {"kind":"scene","index":1,"width":10,"height":10,"boxes":[],"zoom":%s}'
    report = LayoutReport.from_lines([line % 1.0, "noise", line % 1.2])
    assert [s.zoom for s in report.shots] == [1.2]


def test_a_resumed_run_reenters_the_repair_loop_and_the_loop_is_bounded():
    state = SimpleNamespace()

    def edges(**ctx):
        invocation = {"ctx": SimpleNamespace(**ctx)}
        return (
            critic_passed(state, invocation_state=invocation),
            critic_failed(state, invocation_state=invocation),
            review_failed(state, invocation_state=invocation),
        )

    assert edges(critic_passed=True, review_passed=None, review_rounds=0) == (True, False, False)
    # The cut failed review and the run resumed at `critic`: it must go to `fix`, not re-render the same cut.
    assert edges(critic_passed=True, review_passed=False, review_rounds=1) == (False, True, True)
    # Out of rounds: nothing is ready, so the graph ends and the run stops with the report.
    assert edges(critic_passed=True, review_passed=False, review_rounds=MAX_REVIEW_ROUNDS + 1) == (False, False, False)


def test_the_plan_holds_each_scene_to_what_can_be_read_while_its_narration_plays():
    from pydantic import ValidationError

    from reelhive.agents.plan import reading_budget, scene_plan_model

    rate = 161 / 60  # a fixed rate keeps the budget arithmetic below readable
    assert reading_budget(9, 0.0, rate) == 13 and reading_budget(9, 2.0, rate) == 21  # a hold buys reading time
    plan = scene_plan_model([9], rate)
    bullets = {"template": "bullets", "headline": "Mapped to your frameworks", "items": ["ISO 27001 controls"] * 5}
    with pytest.raises(ValidationError, match="scene 1: 19 on-screen words, at most 13 for 9 words of narration"):
        plan(scenes=[bullets])
    assert plan(scenes=[{**bullets, "hold": 2.0}])  # or give it a moment to read
    longer = " ".join(["word"] * 15)  # the fixer may lengthen the narration instead
    assert plan(scenes=[{**bullets, "narration": longer}])
    assert plan.__name__ == "ScenePlan"
