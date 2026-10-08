"""config.yaml: which provider and models each agent tier uses (plan §3.5)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

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
    level: Literal["small", "medium", "high"] = "small"
    format: Literal["16:9", "9:16", "1:1"] = "16:9"
    voice: Voice = Voice()
    music_mood: Literal["calm", "upbeat", "tech", "dramatic", "inspiring"] | None = None
    credit: Literal["end", "corner"] = "end"


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Provider = "claude"
    models: dict[str, Tiers] = Field(
        default_factory=lambda: {"claude": Tiers(strong="claude-sonnet-5-5", fast="claude-haiku-5-5")}
    )
    nodes: dict[Literal["script", "scenes", "music", "critic", "fix"], Provider] = Field(default_factory=dict)
    tier_providers: dict[Literal["strong", "fast"], Provider] = Field(default_factory=dict)
    defaults: Defaults = Defaults()
    ollama_host: str = "http://localhost:11434"
    image_generation: ImageGeneration | None = None
    max_tokens: int = Field(8000, ge=1)
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
