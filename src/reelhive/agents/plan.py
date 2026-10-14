"""Structured output shared by the scene planner and the fixer."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, model_validator

from reelhive.schemas.scene_spec import (
    MAX_HOLD,
    BulletsScene,
    BulletsText,
    CtaScene,
    CtaText,
    FeatureCardScene,
    FeatureCardText,
    HookScene,
    HookText,
    ImageScene,
    IntroText,
    ProblemScene,
    ScreenshotScene,
    StatScene,
    StatText,
    VisualRequest,
)
from reelhive.schemas.scene_spec import Scene as SceneT

TEXT_MODELS: dict[str, type[BaseModel]] = {
    "hook": HookText,
    "feature-card": FeatureCardText,
    "cta": CtaText,
    "image-full": HookText,
    "screenshot-pan": HookText,
    "problem": HookText,
    "stat": StatText,
    "bullets": BulletsText,
}
SCENE_MODELS: dict[str, type[BaseModel]] = {
    "hook": HookScene,
    "feature-card": FeatureCardScene,
    "cta": CtaScene,
    "image-full": ImageScene,
    "screenshot-pan": ScreenshotScene,
    "problem": ProblemScene,
    "stat": StatScene,
    "bullets": BulletsScene,
}


VISUAL_TEMPLATES = ("image-full", "screenshot-pan")
READ_WPS = 4.0  # on-screen words a viewer can take in per second while also listening


def screen_words(scene: Any) -> int:
    """Words a viewer has to read in a scene: headline, supporting text and bullets (labels and URLs are glanced)."""
    return text_words(scene.text)


def text_words(text: Any) -> int:
    """The same count for a scene's text alone."""
    parts = [getattr(text, f, None) or "" for f in ("headline", "subline", "body")]
    return sum(len(p.split()) for p in parts + list(getattr(text, "items", None) or []))


COLD_OPEN = ("hook", "problem")  # a first scene of these plays before the intro screen


def intro_position(scenes: list[Any], cold_open: bool = False) -> int:
    """The intro screen opens the video. With the brief's `cold_open`, an opening hook plays first and the intro
    follows it."""
    return 1 if cold_open and scenes and scenes[0].template in COLD_OPEN else 0


class PlannedScene(BaseModel):
    template: Literal["hook", "feature-card", "cta", "image-full", "screenshot-pan", "problem", "stat", "bullets"]
    headline: str = Field(description="Main on-screen line. Limits: hook 48, feature-card 40, cta 60 chars")
    secondary: str | None = Field(
        None, description="hook/cta: subline (80/60 chars); feature-card: body (110 chars). Optional"
    )
    label: str | None = Field(None, description="feature-card only: a short marker such as 01 (max 4 chars)")
    covers: list[int] = Field(
        default_factory=list, description="Numbers (1-based) of the brief's key-point notes this scene tells"
    )
    narration: str | None = Field(None, description="Spoken text for this scene; set it only when asked to")

    visual_request: VisualRequest = VisualRequest()
    layout: Literal["center", "split-left", "split-right"] = Field(
        "center",
        description="image-full/screenshot-pan only: the visual centred above the text, or left or right of it",
    )
    hold: float = Field(
        0.0, ge=0, le=MAX_HOLD, description="Seconds the settled frame stays after the narration; 0 for none"
    )

    items: list[str] | None = None

    def text(self) -> BaseModel:
        fields = {"headline": self.headline}
        if self.template == "bullets":
            return BulletsText(headline=self.headline, items=self.items or [self.secondary or self.headline])
        if self.secondary:
            fields["body" if self.template == "feature-card" else "subline"] = self.secondary
        if self.template == "feature-card" and self.label:
            fields["label"] = self.label
        return TEXT_MODELS[self.template].model_validate(fields)

    @model_validator(mode="after")
    def _fits_template(self) -> PlannedScene:
        try:
            self.text()
        except ValidationError as e:  # surfaced to the model so it can shorten and retry
            raise ValueError(f"text does not fit the {self.template} template: {e.errors()[0]['msg']}") from e
        return self

    def to_scene(self, index: int, narration: str) -> SceneT:
        direction: dict[str, Any] = {"hold": self.hold}
        if self.template in VISUAL_TEMPLATES:
            direction["layout"] = self.layout
        scene = SCENE_MODELS[self.template](
            index=index,
            narration=narration,
            covers=self.covers,
            text=self.text(),
            visual_request=self.visual_request,
            **direction,
        )
        return scene  # type: ignore[return-value]


def keep_direction(planned: PlannedScene, scene: SceneT, prior: SceneT | None) -> None:
    """Direction the agent left out keeps its earlier value: a repair or regeneration changes only what it names."""
    if prior is None:
        return
    if "visual_request" not in planned.model_fields_set:
        scene.visual_request = prior.visual_request
    if "hold" not in planned.model_fields_set:
        scene.hold = prior.hold
    if "layout" not in planned.model_fields_set and hasattr(prior, "layout") and hasattr(scene, "layout"):
        scene.layout = prior.layout


class ScenePlan(BaseModel):
    intro: IntroText | None = Field(
        None,
        description="The 3-second opening screen. Always set it when planning scenes; when repairing, only if the"
        " failures name it",
    )
    scenes: list[PlannedScene] = Field(min_length=1)


def reading_budget(narration_words: int, hold: float, words_per_second: float) -> int:
    """On-screen words a scene can carry: what a viewer reads (READ_WPS) while its narration plays, plus its hold.
    The same rule as the `reading_time` hard check, applied before the scene is voiced, so it can't fail later."""
    return max(3, int(READ_WPS * (narration_words / words_per_second + hold)))


def scene_plan_model(beat_words: list[int], words_per_second: float, max_words: int = 0) -> type[ScenePlan]:
    """`ScenePlan` that holds each scene's on-screen text to its reading budget. A scene's narration is its own when
    the model writes one (the fixer), else the beat's at the same position (the planner). Over budget goes back to
    the model as a validation error, so the text is cut or the idea split before anything is voiced."""

    class Plan(ScenePlan):
        @model_validator(mode="after")
        def readable(self) -> Plan:
            problems = []
            for i, scene in enumerate(self.scenes):
                if max_words and scene.narration and len(scene.narration.split()) > max_words:
                    problems.append(
                        f"scene {i + 1}: narration of {len(scene.narration.split())} words, at most {max_words} per"
                        " shot; split the scene"
                    )
                spoken = (
                    len(scene.narration.split()) if scene.narration else beat_words[i] if i < len(beat_words) else 0
                )
                if not spoken:
                    continue
                budget = reading_budget(spoken, scene.hold, words_per_second)
                shown = text_words(scene.text())
                if shown > budget:
                    problems.append(
                        f"scene {i + 1}: {shown} on-screen words, at most {budget} for {spoken} words of narration"
                    )
            if problems:
                raise ValueError(
                    "scenes must be short and readable: fewer on-screen words or bullets, a narration that fits one "
                    "shot, or the idea split across scenes: " + "; ".join(problems)
                )
            return self

    Plan.__name__ = Plan.__qualname__ = "ScenePlan"  # the output tool keeps its name
    return Plan


def brief_block(ctx_brief: BaseModel) -> str:
    return (
        "Brief (the user's notes: `features` are numbered key points, `closing` is the idea for the call to"
        " action; treat both as rough input, not as copy):\n" + ctx_brief.model_dump_json(indent=2)
    )


def notes_block(brief: BaseModel) -> str:
    return "Key points:\n" + "\n".join(f"{i}. {note}" for i, note in enumerate(getattr(brief, "features", []), 1))


def research_block(ctx: Any) -> str:
    """Product notes from the `research` step, if it ran (also read back from research.json after a pause)."""
    research = getattr(ctx, "research", None)
    path = ctx.run_dir / "research.json"
    if research is None and path.exists():
        research = json.loads(path.read_text())
    if not research:
        return ""
    return "\n\nProduct research from the website and documents (facts and correct names to build on):\n" + json.dumps(
        research, indent=2
    )
