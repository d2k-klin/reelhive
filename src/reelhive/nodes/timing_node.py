"""Scene lengths from real audio, padded to land on the target duration."""

from __future__ import annotations

import os

from reelhive.core.context import RunContext
from reelhive.nodes.base import FunctionNode
from reelhive.schemas.brief import Brief
from reelhive.schemas.scene_spec import CREDIT_SECONDS, Credit, SceneSpec

WPM_TARGET = 145  # what the script writer aims for; the pace check allows 130-170
LEAD = 0.3  # silence before the voice starts in each scene (covers the fade-in)
TAIL = 0.7  # breathing room after the voice
TAIL_MIN = 0.3
MAX_EXTRA = 3.0  # most padding added per scene before we'd rather lengthen the script
FPS = 30


def credit_for(brief: Brief) -> Credit | None:
    """The visible credit (plan §3.7). Only the env var can turn it off, never the brief."""
    if os.environ.get("REELHIVE_DISABLE_CREDIT", "").strip().lower() in ("1", "true", "yes"):
        return None
    return Credit(mode=brief.credit, duration=CREDIT_SECONDS if brief.credit == "end" else 0.0)


def available_seconds(brief: Brief) -> float:
    """Seconds left for scenes once the end credit is counted into the target."""
    credit = credit_for(brief)
    return brief.duration - (credit.duration if credit else 0.0)


def target_words(brief: Brief) -> int:
    return round(available_seconds(brief) * WPM_TARGET / 60)


def _frames(seconds: float) -> float:
    return round(seconds * FPS) / FPS


def apply_timing(spec: SceneSpec, narrated: dict[int, tuple[str, float]], brief: Brief) -> SceneSpec:
    spec.credit = credit_for(brief)
    available = available_seconds(brief)
    base = [narrated[s.index][1] + LEAD + TAIL for s in spec.scenes]
    gap = available - sum(base)
    if gap >= 0:
        delta = min(MAX_EXTRA, gap / len(base))
    else:
        delta = -min(TAIL - TAIL_MIN, -gap / len(base))
    end = 0.0
    for scene, length in zip(spec.scenes, base, strict=True):
        # Round the boundaries, not each length, so frame rounding never accumulates.
        scene.audio = f"audio/scene_{scene.index:02d}.wav"
        scene.start = _frames(end)
        end += length + delta
        scene.duration = round(_frames(end) - scene.start, 4)
    spec.duration = round(_frames(end) + (spec.credit.duration if spec.credit else 0.0), 3)
    return spec


class TimingNode(FunctionNode):
    name = "timing"

    def run(self, ctx: RunContext) -> None:
        assert ctx.spec
        if ctx.music:
            ctx.spec.music = ctx.music["file"]
        apply_timing(ctx.spec, ctx.narrated, ctx.brief)
        ctx.events.emit(
            "node.task",
            node=self.name,
            task=f"{len(ctx.spec.scenes)} scenes, {ctx.spec.duration:.1f}s of {ctx.brief.duration}s",
        )
