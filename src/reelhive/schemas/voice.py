from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Voice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    gender: Literal["female", "male"] = "female"
    accent: Literal["us", "uk"] = "us"
    speed: float = Field(1.0, ge=0.8, le=1.2)
