"""config.yaml: which provider and models each agent tier uses (plan §3.5)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from reelhive.schemas.voice import Voice

REPO_ROOT = Path(__file__).resolve().parents[2]  # cloning is the install method (plan §10)


class Tiers(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strong: str
    fast: str


Provider = Literal["claude", "bedrock", "openai", "ollama", "copilot"]


class ImageGeneration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str
    cost_per_image: float | None = Field(None, ge=0, description="Optional USD estimate from your pricing")


class Defaults(BaseModel):
    model_config = ConfigDict(extra="forbid")
    level: Literal["low", "medium", "high"] = "low"

    @field_validator("level", mode="before")
    @classmethod
    def legacy_level(cls, value: object) -> object:
        return "low" if value == "small" else value

    format: Literal["16:9", "9:16", "1:1"] = "16:9"
    voice: Voice = Voice()
    music_mood: Literal["calm", "upbeat", "tech", "dramatic", "inspiring"] | None = None
    credit: Literal["end", "corner"] = "end"


class _Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")


class YouTubeSettings(_Settings):
    privacy: Literal["private", "unlisted", "public"] = "private"
    category_id: str = Field("28", pattern=r"^\d+$", description="YouTube category; 28 is Science & Technology")
    notify_subscribers: bool = False


class LinkedInSettings(_Settings):
    organization: str | None = Field(
        None, pattern=r"^urn:li:organization:\d+$", description="Post as this page; otherwise as the signed-in member"
    )
    visibility: Literal["PUBLIC", "CONNECTIONS"] = "PUBLIC"
    api_version: str = Field("202609", pattern=r"^\d{6}$", description="LinkedIn-Version header (YYYYMM)")


class TikTokSettings(_Settings):
    mode: Literal["draft", "direct"] = Field(
        "draft", description="draft: sent to your TikTok inbox to finish in the app; direct: posted straight away"
    )
    privacy: Literal["PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "FOLLOWER_OF_CREATOR", "SELF_ONLY"] = "SELF_ONLY"
    allow_comments: bool = True
    allow_duet: bool = False
    allow_stitch: bool = False


class InstagramSettings(_Settings):
    share_to_feed: bool = True
    account: str | None = Field(None, description="Instagram username to post as, when several are linked")
    config_id: str | None = Field(
        None, description="Facebook Login for Business configuration id, if your app uses one"
    )


class Publishing(_Settings):
    """Where and how videos are published. Client ids and secrets come from environment variables only."""

    redirect_port: int = Field(8765, ge=1024, le=65535, description="Loopback port for sign-in redirects")
    label_ai: bool = Field(True, description="Label posts as AI-generated where the platform supports it")
    youtube: YouTubeSettings = YouTubeSettings()
    linkedin: LinkedInSettings = LinkedInSettings()
    tiktok: TikTokSettings = TikTokSettings()
    instagram: InstagramSettings = InstagramSettings()


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Provider = "claude"
    models: dict[str, Tiers] = Field(
        default_factory=lambda: {"claude": Tiers(strong="claude-sonnet-5-5", fast="claude-haiku-5-5")}
    )
    nodes: dict[
        Literal["research", "script", "scenes", "music", "critic", "fix", "review", "sound", "publish"], Provider
    ] = Field(default_factory=dict)
    tier_providers: dict[Literal["strong", "fast"], Provider] = Field(default_factory=dict)
    defaults: Defaults = Defaults()
    ollama_host: str = "http://localhost:11434"
    image_generation: ImageGeneration | None = None
    max_tokens: int = Field(8000, ge=1)
    publishing: Publishing = Publishing()
    runs_dir: Path = Path("runs")

    def provider_for(self, node: str, tier: str) -> str:
        node_provider = next((provider for name, provider in self.nodes.items() if name == node), None)
        tier_provider = next((provider for name, provider in self.tier_providers.items() if name == tier), None)
        return node_provider or tier_provider or self.provider


def load_config(path: Path | None = None) -> Config:
    """Explicit path, else ./config.yaml if present, else defaults."""
    path = path or (Path("config.yaml") if Path("config.yaml").exists() else None)
    if path is None:
        return Config()
    return Config.model_validate(yaml.safe_load(path.read_text()) or {})
