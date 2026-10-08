"""The scene spec: the render contract between Python and renderer/ (plan §3.2).

Character limits live here as maxLength and reach the renderer through the exported
JSON Schema (renderer/src/spec.schema.json), so there is one source of truth.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field

FORMATS = {"16:9": (1920, 1080)}
CREDIT_TEXT = "Made with ReelHive by Mr.D"  # mirrors renderer/src/templates/credit.tsx (contract-tested)
CREDIT_SECONDS = 1.5


class HookText(BaseModel):
    headline: str = Field(max_length=48)
    subline: str | None = Field(None, max_length=80)


class FeatureCardText(BaseModel):
    label: str | None = Field(None, max_length=4, description="Short marker such as 01")
    headline: str = Field(max_length=40)
    body: str | None = Field(None, max_length=110)


class CtaText(BaseModel):
    headline: str = Field(max_length=60)
    subline: str | None = Field(None, max_length=60)


class _SceneBase(BaseModel):
    index: int = Field(ge=1)
    narration: str
    feature: str | None = None
    audio: str | None = Field(None, description="Narration WAV, relative to the run folder")
    start: float = 0.0
    duration: float = 0.0


class HookScene(_SceneBase):
    template: Literal["hook"] = "hook"
    text: HookText


class FeatureCardScene(_SceneBase):
    template: Literal["feature-card"] = "feature-card"
    text: FeatureCardText


class CtaScene(_SceneBase):
    template: Literal["cta"] = "cta"
    text: CtaText


Scene = Annotated[HookScene | FeatureCardScene | CtaScene, Field(discriminator="template")]
TEMPLATES = ("hook", "feature-card", "cta")


class Credit(BaseModel):
    mode: Literal["end", "corner"]
    text: str = CREDIT_TEXT
    duration: float = Field(description="Seconds the end card takes; 0 for corner")


class SceneSpec(BaseModel):
    version: int = 1
    format: str = "16:9"
    width: int = 1920
    height: int = 1080
    fps: int = 30
    duration: float = 0.0
    scenes: list[Scene]
    credit: Credit | None = None
    music: str | None = Field(None, description="Music file chosen from the library")


def export_schema(path: Path) -> str:
    text = json.dumps(SceneSpec.model_json_schema(), indent=2) + "\n"
    path.write_text(text)
    return text


if __name__ == "__main__":  # python -m reelhive.schemas.scene_spec
    export_schema(Path(__file__).parents[3] / "renderer" / "src" / "spec.schema.json")
