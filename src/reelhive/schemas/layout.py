"""The layout report: what the renderer actually put on screen, measured in the rendered frame.

The renderer measures every shot once its entrance has settled and prints one `REELHIVE_LAYOUT` line per
shot; `render/bridge.py` collects them into `render/layout.json`. The `review` node checks it against the
layout gates, so clipped, overlapping, tiny or blurry elements are caught from real geometry, not guessed
from character counts.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

LAYOUT_MARKER = "REELHIVE_LAYOUT "


class Box(BaseModel):
    role: Literal[
        "headline", "subline", "body", "label", "item", "url", "title", "tagline", "caption", "visual", "logo"
    ]
    x: float = Field(description="Left edge in frame pixels, from the frame's left")
    y: float = Field(description="Top edge in frame pixels, from the frame's top")
    width: float = Field(ge=0)
    height: float = Field(ge=0)
    font_size: float | None = Field(None, description="Text only: rendered size in pixels")
    text: str | None = None


class ShotLayout(BaseModel):
    kind: Literal["intro", "scene"]
    index: int = Field(ge=0, description="Scene index; 0 for the intro screen")
    width: int
    height: int
    boxes: list[Box] = Field(default_factory=list)
    zoom: float = Field(
        1.0, ge=0, description="Visual only: image pixels drawn per source pixel at the closest framing (>1 upscales)"
    )


class LayoutReport(BaseModel):
    shots: list[ShotLayout] = Field(default_factory=list)

    @classmethod
    def from_lines(cls, lines: list[str]) -> LayoutReport:
        """Shots from renderer output. A shot can be printed more than once (Revideo walks the timeline before it
        draws frames), so the last measurement of each shot wins."""
        shots: dict[tuple[str, int], ShotLayout] = {}
        for line in lines:
            if LAYOUT_MARKER in line:
                shot = ShotLayout.model_validate_json(line.split(LAYOUT_MARKER, 1)[1])
                shots[(shot.kind, shot.index)] = shot
        return cls(shots=sorted(shots.values(), key=lambda s: (s.kind != "intro", s.index)))
