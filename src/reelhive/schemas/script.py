"""The script: narration split into beats, one beat per scene."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Beat(BaseModel):
    role: Literal["hook", "problem", "feature", "cta"] = Field(description="What this beat does in the story")
    narration: str = Field(min_length=1, description="Exactly what the voice says in this beat")
    feature: str | None = Field(None, description="For feature beats: the brief feature this beat covers, verbatim")


class Script(BaseModel):
    title: str
    beats: list[Beat] = Field(min_length=2, max_length=12)
