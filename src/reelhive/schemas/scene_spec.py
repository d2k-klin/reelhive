"""The scene spec: the render contract between Python and renderer/ (plan §3.2).

Character limits live here as maxLength and reach the renderer through the exported
JSON Schema (renderer/src/spec.schema.json), so there is one source of truth.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, model_validator

from reelhive.schemas.voice import Voice

FORMATS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}
CREDIT_TEXT = "Made with ReelHive by Mr.D"  # mirrors renderer/src/templates/credit.tsx (contract-tested)
CREDIT_SECONDS = 1.5
INTRO_SECONDS = 3.0
MAX_HOLD = 3.0


def display_url(raw: str | None) -> str | None:
    """A site address as people say it: no scheme, `www.`, query or trailing slash. None if it can't fit."""
    if not raw:
        return None
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.hostname or "").removeprefix("www.")
    if not host:
        return None
    shown = host + parsed.path.rstrip("/")
    shown = shown if len(shown) <= 60 else host
    return shown if len(shown) <= 60 else None


class IntroText(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(
        min_length=1,
        max_length=40,
        description="The product or brand name, spelled and capitalised exactly as its owner writes it",
    )
    tagline: str | None = Field(
        None, max_length=80, description="What it is, in one short line: a claim, not details or key points"
    )


class Intro(IntroText):
    """The opening screen shown before the first scene; it has no narration."""

    url: str | None = Field(None, max_length=60, description="Site address, shown small; set from the brief")
    duration: float = Field(INTRO_SECONDS, ge=1, le=10)


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
    url: str | None = Field(None, max_length=60, description="Site address, shown small; set from the brief")


class VisualRequest(BaseModel):
    kind: Literal["product_ui", "concept", "none"] = "none"
    image: str | None = Field(None, description="Filename from the provided image catalog")
    clip: str | None = Field(
        None, description="Filename from the provided clip catalog: the user's own video, played muted in the scene"
    )
    route: str | None = Field(None, description="Route from the screenshot catalog")
    region: str | None = Field(
        None, description="Region id from that screenshot page's `regions` to close in on; product UI only"
    )
    prompt: str | None = Field(None, description="Concept illustration only; never product UI")


class Focus(BaseModel):
    """A part of the image to close in on, as fractions of the image's width and height."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)
    label: str = Field("", max_length=120, description="What the region shows, as measured on the page")

    @model_validator(mode="after")
    def inside(self) -> Focus:
        if self.x + self.width > 1.0001 or self.y + self.height > 1.0001:
            raise ValueError("focus region must lie inside the image")
        return self


class VisualAsset(BaseModel):
    source: Literal["provided", "screenshot", "generated"]
    file: str
    media: Literal["image", "video"] = "image"
    frame: Literal["browser", "phone", "none"] = "none"
    focus: Focus | None = Field(None, description="Resolved from visual_request.region when the image is captured")
    duration: float | None = Field(
        None, gt=0, description="Video only: seconds the clip plays; the last frame holds if the scene runs longer"
    )
    width: int | None = Field(None, gt=0, description="Video only: pixel width of the normalized clip")
    height: int | None = Field(None, gt=0, description="Video only: pixel height of the normalized clip")

    @model_validator(mode="after")
    def video_is_measured(self) -> VisualAsset:
        if self.media == "video" and not (self.duration and self.width and self.height):
            raise ValueError("a video visual needs its duration, width and height")
        return self


class Theme(BaseModel):
    background: str = "#0f1115"
    surface: str = "#1a1d24"
    text: str = "#f5f5f4"
    muted: str = "#a8a29e"
    accent: str = "#f5a524"
    logo: str | None = None


class BulletsText(BaseModel):
    headline: str = Field(max_length=48)
    items: list[str] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def fit(self):
        if any(len(item) > 70 for item in self.items):
            raise ValueError("each bullet must fit 70 characters")
        return self


class StatText(BaseModel):
    headline: str = Field(max_length=20)
    subline: str | None = Field(None, max_length=80)


class Word(BaseModel):
    """One spoken word, timed from the recorded voice (never written by an agent)."""

    text: str = Field(min_length=1, description="The word with any punctuation that follows it")
    start: float = Field(ge=0, description="Seconds from the scene's start")
    end: float = Field(ge=0)


class _SceneBase(BaseModel):
    index: int = Field(ge=1)
    narration: str
    covers: list[int] = Field(default_factory=list, description="Brief key-point notes (1-based) this scene tells")
    duration_override: float | None = Field(None, ge=0.5, le=180)
    voice_override: Voice | None = None
    image_approved: bool = False
    visual_request: VisualRequest = VisualRequest()
    visual: VisualAsset | None = None
    audio: str | None = Field(None, description="Narration WAV, relative to the run folder")
    hold: float = Field(
        0.0, ge=0, le=MAX_HOLD, description="Seconds the settled frame stays after the narration, so it can be read"
    )
    words: list[Word] = Field(default_factory=list, description="The narration's words as spoken; set by timing")
    start: float = 0.0
    duration: float = 0.0


class HookScene(_SceneBase):
    template: Literal["hook"] = "hook"
    text: HookText


class FeatureCardScene(_SceneBase):
    template: Literal["feature-card"] = "feature-card"
    text: FeatureCardText


class _VisualScene(_SceneBase):
    layout: Literal["center", "split-left", "split-right"] = Field(
        "center", description="Where the visual sits: centred above the text, or on the left or right of it"
    )


class ImageScene(_VisualScene):
    template: Literal["image-full"] = "image-full"
    text: HookText


class ScreenshotScene(_VisualScene):
    template: Literal["screenshot-pan"] = "screenshot-pan"
    text: HookText


class CtaScene(_SceneBase):
    template: Literal["cta"] = "cta"
    text: CtaText


class ProblemScene(_SceneBase):
    template: Literal["problem"] = "problem"
    text: HookText


class StatScene(_SceneBase):
    template: Literal["stat"] = "stat"
    text: StatText


class BulletsScene(_SceneBase):
    template: Literal["bullets"] = "bullets"
    text: BulletsText


Scene = Annotated[
    HookScene | FeatureCardScene | CtaScene | ImageScene | ScreenshotScene | ProblemScene | StatScene | BulletsScene,
    Field(discriminator="template"),
]
TEMPLATES = ("hook", "feature-card", "cta", "image-full", "screenshot-pan", "problem", "stat", "bullets")


class Motion(BaseModel):
    """Timing of the renderer's motion language, set by code so Python's checks and the renderer agree."""

    enter: float = Field(0.8, gt=0, description="Seconds a shot's elements take to arrive, staggered in reading order")
    transition: float = Field(0.6, gt=0, description="Seconds the outgoing shot overlaps the start of the incoming one")


class Credit(BaseModel):
    mode: Literal["end", "corner"]
    text: str = CREDIT_TEXT
    duration: float = Field(description="Seconds the end card takes; 0 for corner")


class SoundCue(BaseModel):
    """One sound effect in the mix, placed by the `sound` node on a moment the renderer reported."""

    effect: str = Field(description="Effect file from assets/sfx/manifest.json")
    moment: str = Field(description="The moment it scores, e.g. 'scene 3 cut' (see render/layout.json)")
    at: float = Field(ge=0, description="Seconds into the video the effect starts: its peak lands on the moment")
    gain_db: float = Field(ge=-36, le=-6, description="Level in the mix; music sits around -10 dB under the voice")


class SceneSpec(BaseModel):
    version: int = 2
    format: str = "16:9"
    width: int = 1920
    height: int = 1080
    fps: int = 30
    duration: float = 0.0
    theme: Theme = Theme()
    motion: Motion = Motion()
    captions: bool = Field(False, description="Show the narration as word-by-word captions; set from the brief")
    intro: Intro | None = None
    intro_at: int = Field(
        0, ge=0, description="Scenes played before the intro screen: 0 opens with it, 1 is a cold open after the hook"
    )
    scenes: list[Scene] = Field(min_length=1)
    credit: Credit | None = None
    music_volume: float = Field(0.3, ge=0, le=1)
    music: str | None = Field(None, description="Music file chosen from the library")
    sound_effects: list[SoundCue] = Field(
        default_factory=list, description="Sound effects in the mix; often none. Set by the `sound` node"
    )

    @model_validator(mode="after")
    def intro_in_range(self) -> SceneSpec:
        if self.intro_at > len(self.scenes):
            raise ValueError("intro_at is past the last scene")
        return self

    def timeline(self) -> list[Intro | Scene]:
        """What plays, in order: the scenes with the intro screen inserted at `intro_at`."""
        items: list[Intro | Scene] = list(self.scenes)
        if self.intro:
            items.insert(self.intro_at, self.intro)
        return items


def export_schema(path: Path) -> str:
    text = json.dumps(SceneSpec.model_json_schema(), indent=2) + "\n"
    path.write_text(text)
    return text


if __name__ == "__main__":  # python -m reelhive.schemas.scene_spec
    export_schema(Path(__file__).parents[3] / "renderer" / "src" / "spec.schema.json")
