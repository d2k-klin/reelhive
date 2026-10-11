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
COLD_OPEN = ("hook", "problem")  # a first scene of these plays before the intro screen


def intro_position(scenes: list[Any]) -> int:
    """Hook first, then the product: the intro screen follows an opening hook (a cold open)."""
    return 1 if scenes and scenes[0].template in COLD_OPEN else 0


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
