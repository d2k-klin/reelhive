"""The brief: what the user asks for (plan §4)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Voice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gender: Literal["female", "male"] = "female"
    accent: Literal["us", "uk"] = "us"
    speed: float = Field(1.0, ge=0.8, le=1.2)


class Brief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: Literal["small", "medium", "high"] = "small"
    audience: str = Field(min_length=3)
    storyline: str = Field(min_length=3)
    features: list[str] = Field(min_length=1, max_length=8)
    duration: int = Field(60, ge=15, le=180, description="Target length in seconds")
    format: Literal["16:9", "9:16", "1:1"] = "16:9"
    voice: Voice = Voice()
    closing: str = Field(min_length=3, max_length=60)
    credit: Literal["end", "corner"] = "end"

    # ponytail: M1 ships `small` at 16:9; medium/high and the other formats land in M2/M3.
    @field_validator("level")
    @classmethod
    def _level_available(cls, v: str) -> str:
        if v != "small":
            raise ValueError(f"level '{v}' arrives in a later milestone; M1 supports 'small'")
        return v

    @field_validator("format")
    @classmethod
    def _format_available(cls, v: str) -> str:
        if v != "16:9":
            raise ValueError(f"format '{v}' arrives in M2; M1 supports '16:9'")
        return v
