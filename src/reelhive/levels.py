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
        # `low` exposes only voice gender (or a named narrator voice, which brings its own accent); speed is fixed.
        if self.name == "low":
            accent = {} if brief.voice.name else {"accent": "us"}
            return {"voice": brief.voice.model_copy(update={"speed": 1.0, **accent})}
        return {}


LEVELS = {
    "low": Level("low", approval_stops=()),
    "medium": Level("medium", approval_stops=("script",)),
    "high": Level("high", approval_stops=("script", "scenes")),
}
