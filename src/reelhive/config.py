"""config.yaml: which provider and models each agent tier uses (plan §3.5)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

REPO_ROOT = Path(__file__).resolve().parents[2]  # cloning is the install method (plan §10)


class Tiers(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strong: str
    fast: str


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["claude", "bedrock", "openai", "ollama", "copilot"] = "claude"
    models: dict[str, Tiers] = Field(
        default_factory=lambda: {"claude": Tiers(strong="claude-sonnet-5-5", fast="claude-haiku-5-5")}
    )
    max_tokens: int = 8000
    runs_dir: Path = Path("runs")


def load_config(path: Path | None = None) -> Config:
    """Explicit path, else ./config.yaml if present, else defaults."""
    path = path or (Path("config.yaml") if Path("config.yaml").exists() else None)
    if path is None:
        return Config()
    return Config.model_validate(yaml.safe_load(path.read_text()) or {})
