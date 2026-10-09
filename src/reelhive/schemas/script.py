"""The script: narration split into beats, one beat per scene."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Beat(BaseModel):
    role: Literal["hook", "problem", "feature", "cta"] = Field(description="What this beat does in the story")
    narration: str = Field(min_length=1, description="Exactly what the voice says in this beat")
    covers: list[int] = Field(
        default_factory=list,
        description="Numbers (1-based) of the brief's key-point notes this beat tells; a beat may cover several",
    )


class Script(BaseModel):
    title: str
    beats: list[Beat] = Field(min_length=2, max_length=12)
