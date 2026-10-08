"""What each customization level fills from defaults and where runs pause (plan §4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from reelhive.schemas.brief import Brief


@dataclass(frozen=True)
class Level:
    name: str
    approval_stops: tuple[str, ...]

    def defaults(self, brief: Brief) -> dict[str, Any]:
        # `small` exposes only voice gender; accent and speed are fixed to the defaults.
        if self.name == "small":
            return {"voice": brief.voice.model_copy(update={"accent": "us", "speed": 1.0})}
        return {}


LEVELS = {"small": Level("small", approval_stops=()), "medium": Level("medium", approval_stops=("script",))}
