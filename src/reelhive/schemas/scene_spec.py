"""The scene spec: the render contract between Python and renderer/ (plan §3.2).

Character limits live here as maxLength and reach the renderer through the exported
JSON Schema (renderer/src/spec.schema.json), so there is one source of truth.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field

FORMATS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}
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


class VisualRequest(BaseModel):
    kind: Literal["product_ui", "concept", "none"] = "none"
    image: str | None = Field(None, description="Filename from the provided image catalog")
    route: str | None = Field(None, description="Route from the screenshot catalog")
    prompt: str | None = Field(None, description="Concept illustration only; never product UI")


class VisualAsset(BaseModel):
    source: Literal["provided", "screenshot", "generated"]
    file: str
    frame: Literal["browser", "phone", "none"] = "none"


class Theme(BaseModel):
    background: str = "#0f1115"
    surface: str = "#1a1d24"
    text: str = "#f5f5f4"
    muted: str = "#a8a29e"
    accent: str = "#f5a524"
    logo: str | None = None


class _SceneBase(BaseModel):
    index: int = Field(ge=1)
    narration: str
    feature: str | None = None
    visual_request: VisualRequest = VisualRequest()
    visual: VisualAsset | None = None
    audio: str | None = Field(None, description="Narration WAV, relative to the run folder")
    start: float = 0.0
    duration: float = 0.0


class HookScene(_SceneBase):
    template: Literal["hook"] = "hook"
    text: HookText


class FeatureCardScene(_SceneBase):
    template: Literal["feature-card"] = "feature-card"
    text: FeatureCardText


class ImageScene(_SceneBase):
    template: Literal["image-full"] = "image-full"
    text: HookText


class ScreenshotScene(_SceneBase):
    template: Literal["screenshot-pan"] = "screenshot-pan"
    text: HookText


class CtaScene(_SceneBase):
    template: Literal["cta"] = "cta"
    text: CtaText


Scene = Annotated[
    HookScene | FeatureCardScene | CtaScene | ImageScene | ScreenshotScene, Field(discriminator="template")
]
TEMPLATES = ("hook", "feature-card", "cta", "image-full", "screenshot-pan")


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
    theme: Theme = Theme()
    scenes: list[Scene] = Field(min_length=1)
    credit: Credit | None = None
    music: str | None = Field(None, description="Music file chosen from the library")


def export_schema(path: Path) -> str:
    text = json.dumps(SceneSpec.model_json_schema(), indent=2) + "\n"
    path.write_text(text)
    return text


if __name__ == "__main__":  # python -m reelhive.schemas.scene_spec
    export_schema(Path(__file__).parents[3] / "renderer" / "src" / "spec.schema.json")
