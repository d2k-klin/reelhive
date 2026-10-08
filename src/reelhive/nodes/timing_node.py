"""Scene lengths from real audio, padded to land on the target duration."""

from __future__ import annotations

import os

from reelhive.core.context import RunContext
from reelhive.nodes.base import FunctionNode
from reelhive.schemas.brief import Brief
from reelhive.schemas.scene_spec import CREDIT_SECONDS, Credit, SceneSpec

WPM_TARGET = 145  # what the script writer aims for; the pace check allows 130-170
SPEECH_WPM = 161  # measured Kokoro rate at speed 1.0 (docs/plan.md, M1 notes)
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
    """Words for the whole script. Short videos are capped so the voice plus each scene's minimum
    padding still fits the target (found by the M4 evals: 15-20s briefs overran by 6-8%)."""
    available = available_seconds(brief)
    scenes = len(brief.features) + 3  # hook, problem, one per feature, cta
    fits = (available - scenes * (LEAD + TAIL_MIN)) * SPEECH_WPM * brief.voice.speed / 60
    return round(min(available * WPM_TARGET / 60, fits))


def _frames(seconds: float) -> float:
    return round(seconds * FPS) / FPS


def apply_timing(spec: SceneSpec, narrated: dict[int, tuple[str, float]], brief: Brief) -> SceneSpec:
    spec.credit = credit_for(brief)
    available = available_seconds(brief)
    base = [narrated[s.index][1] + LEAD + TAIL for s in spec.scenes]
    flexible = sum(s.duration_override is None for s in spec.scenes)
    gap = available - sum(
        s.duration_override if s.duration_override is not None else length
        for s, length in zip(spec.scenes, base, strict=True)
    )
    if gap >= 0:
        delta = min(MAX_EXTRA, gap / max(1, flexible))
    else:
        delta = -min(TAIL - TAIL_MIN, -gap / max(1, flexible))
    end = 0.0
    for scene, length in zip(spec.scenes, base, strict=True):
        # Round the boundaries, not each length, so frame rounding never accumulates.
        scene.audio = f"audio/scene_{scene.index:02d}.wav"
        scene.start = _frames(end)
        end += scene.duration_override if scene.duration_override is not None else length + delta
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
