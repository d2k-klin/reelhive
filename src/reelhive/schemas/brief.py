"""Validated brief and local visual sources (plan §4)."""

from __future__ import annotations

from typing import Annotated, Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from reelhive.schemas.scene_spec import Scene
from reelhive.schemas.voice import Voice

Color = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]


class Options(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Brand(Options):
    colors: list[Color] = Field(default_factory=list, max_length=3, description="Accent, background, text")
    logo: str | None = None


class Screenshots(Options):
    url: str
    routes: list[str] = Field(default_factory=list, max_length=10)
    storage_state: str | None = None
    mask: list[str] = Field(default_factory=list)
    frame: Literal["browser", "phone", "none"] = "none"

    @field_validator("url")
    @classmethod
    def http_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("use an http(s) URL without embedded credentials")
        return value


class Images(Options):
    dir: str
    captions: str | None = None
    describe_images: bool = False


class Generate(Options):
    provider: Literal["openai"] = "openai"
    style: str = ""
    max_images: int = Field(6, ge=0, le=20)


class Visuals(Options):
    source: Literal["auto", "screenshots", "images", "generate", "none"] = "auto"
    url: str | None = None
    screenshots: Screenshots | None = None
    images: Images | str | None = None
    generate: Generate | bool = False

    @model_validator(mode="after")
    def expand_shortcuts(self) -> Visuals:
        if self.url:
            if self.screenshots:
                raise ValueError("use either visuals.url or visuals.screenshots")
            self.screenshots = Screenshots(url=self.url)
            self.url = None
        if isinstance(self.images, str):
            self.images = Images(dir=self.images)
        if isinstance(self.images, Images) and not self.images.dir.strip():
            self.images = None  # a blank folder would otherwise resolve to the working directory
        if self.generate is True:
            self.generate = Generate()
        required = {"screenshots": self.screenshots, "images": self.images, "generate": self.generate}
        if self.source in required and not required[self.source]:
            raise ValueError(f"visuals.source={self.source} requires its source settings")
        return self


class Brief(Options):
    level: Literal["low", "medium", "high"] = Field(
        "low", description="Customization level: low = agents decide most, high = you direct every scene"
    )
    audience: str = Field(min_length=3)
    storyline: str = Field(min_length=3)
    features: list[str] = Field(
        min_length=1, max_length=8, description="Key points as rough notes; the agents research them and write the copy"
    )
    duration: int = Field(60, ge=15, le=180)
    format: Literal["16:9", "9:16", "1:1"] = "16:9"
    voice: Voice = Voice()
    closing: str = Field(
        min_length=3,
        max_length=200,
        description="The idea of the closing call to action; the agents polish the wording",
    )
    website: str | None = Field(
        None, max_length=300, description="Product website: researched for the story and used for screenshots"
    )
    credit: Literal["end", "corner"] = "end"
    tone: str = "clear and direct"
    pacing: Literal["slow", "balanced", "fast"] = "balanced"
    brand: Brand = Brand()
    theme: Literal["default", "dark", "brand"] = "default"
    music_mood: Literal["calm", "upbeat", "dramatic", "inspiring", "tech"] | None = None
    cta_url: str | None = Field(None, max_length=60)
    visuals: Visuals = Visuals()

    scenes: list[Scene] | None = Field(None, min_length=1, max_length=12)
    music_track: str | None = None
    music_volume: float = Field(0.3, ge=0, le=1)

    @field_validator("level", mode="before")
    @classmethod
    def legacy_level(cls, value: Any) -> Any:
        return "low" if value == "small" else value  # briefs written before 0.4 said "small"

    @field_validator("website")
    @classmethod
    def website_url(cls, value: str | None) -> str | None:
        if value:
            Screenshots(url=value)  # same rule: http(s), no embedded credentials
        return value or None

    @model_validator(mode="before")
    @classmethod
    def screenshots_from_website(cls, data: Any) -> Any:
        """A product website doubles as the screenshot source unless the brief says otherwise."""
        if isinstance(data, dict) and data.get("website"):
            visuals = dict(data.get("visuals") or {})
            if visuals.get("source", "auto") in ("auto", "screenshots") and not (
                visuals.get("url") or visuals.get("screenshots")
            ):
                visuals["url"] = data["website"]
                data = {**data, "visuals": visuals}
        return data
