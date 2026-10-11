"""Scene lengths from real audio, padded to land on the target duration."""

from __future__ import annotations

import os

from reelhive.core.context import RunContext
from reelhive.nodes.base import FunctionNode
from reelhive.schemas.brief import Brief
from reelhive.schemas.scene_spec import (
    CREDIT_SECONDS,
    INTRO_SECONDS,
    Credit,
    CtaScene,
    Intro,
    SceneSpec,
    Word,
    display_url,
)

# Narration density per brief `pacing`: (lowest, highest, target) words per minute of video. `slow` leaves
# room for the picture (short showcase cuts); `balanced` is the classic narrated explainer.
PACE = {"slow": (100, 135, 115), "balanced": (130, 170, 145), "fast": (145, 175, 160)}
SPEECH_WPM = 161  # measured Kokoro rate at speed 1.0 (docs/plan.md, M1 notes)
LEAD = 0.3  # silence before the voice starts in each scene (covers the fade-in)
TAIL = 0.7  # breathing room after the voice
TAIL_MIN = 0.3
MAX_EXTRA = 3.0  # most padding added per scene before we'd rather lengthen the script
FINAL_HOLD = 1.0  # the closing frame settles this long after the last words, before the credit
FPS = 30


def credit_for(brief: Brief) -> Credit | None:
    """The visible credit (plan §3.7). Only the env var can turn it off, never the brief."""
    if os.environ.get("REELHIVE_DISABLE_CREDIT", "").strip().lower() in ("1", "true", "yes"):
        return None
    return Credit(mode=brief.credit, duration=CREDIT_SECONDS if brief.credit == "end" else 0.0)


def intro_seconds(spec: SceneSpec) -> float:
    return spec.intro.duration if spec.intro else 0.0


def place_urls(spec: SceneSpec, brief: Brief) -> None:
    """The site address is code, not copy: small on the intro, and under the closing call to action."""
    if spec.intro and spec.intro.url is None:
        spec.intro.url = display_url(brief.website or brief.cta_url)
    closing = next((s for s in reversed(spec.scenes) if isinstance(s, CtaScene)), None)
    if closing and closing.text.url is None:
        closing.text.url = display_url(brief.cta_url or brief.website)


def available_seconds(brief: Brief, intro: float = INTRO_SECONDS) -> float:
    """Seconds left for scenes once the intro and the end credit are counted into the target."""
    credit = credit_for(brief)
    return brief.duration - intro - (credit.duration if credit else 0.0)


def target_words(brief: Brief) -> int:
    """Words for the whole script. Short videos are capped so the voice plus each scene's minimum
    padding still fits the target (found by the M4 evals: 15-20s briefs overran by 6-8%)."""
    available = available_seconds(brief)
    scenes = len(brief.features) + 3  # hook, problem, one per feature, cta
    fits = (available - scenes * (LEAD + TAIL_MIN) - FINAL_HOLD) * SPEECH_WPM * brief.voice.speed / 60
    return round(min(available * PACE[brief.pacing][2] / 60, fits))


def holds(spec: SceneSpec) -> dict[int, float]:
    """Seconds each scene stays settled after its narration: the planner's `hold`, and the closing frame's."""
    last = spec.scenes[-1].index
    return {s.index: max(s.hold, FINAL_HOLD if s.index == last else 0.0) for s in spec.scenes}


def _frames(seconds: float) -> float:
    return round(seconds * FPS) / FPS


def apply_timing(
    spec: SceneSpec, narrated: dict[int, tuple[str, float]], brief: Brief, words: dict[int, list[Word]] | None = None
) -> SceneSpec:
    spec.credit = credit_for(brief)
    spec.captions = brief.captions
    place_urls(spec, brief)
    opening = intro_seconds(spec)
    available = available_seconds(brief, opening)
    settle = holds(spec)
    base = [narrated[s.index][1] + LEAD + TAIL + settle[s.index] for s in spec.scenes]
    flexible = sum(s.duration_override is None for s in spec.scenes)
    gap = available - sum(
        s.duration_override if s.duration_override is not None else length
        for s, length in zip(spec.scenes, base, strict=True)
    )
    if gap >= 0:
        delta = min(MAX_EXTRA, gap / max(1, flexible))
    else:
        delta = -min(TAIL - TAIL_MIN, -gap / max(1, flexible))
    lengths = {s.index: length for s, length in zip(spec.scenes, base, strict=True)}
    end = 0.0
    for item in spec.timeline():
        if isinstance(item, Intro):  # silent title screen, wherever `intro_at` puts it
            end += item.duration
            continue
        # Round the boundaries, not each length, so frame rounding never accumulates.
        item.audio = f"audio/scene_{item.index:02d}.wav"
        item.start = _frames(end)
        end += item.duration_override if item.duration_override is not None else lengths[item.index] + delta
        item.duration = round(_frames(end) - item.start, 4)
        # Captions follow the voice, which the mix places LEAD seconds into the scene.
        item.words = [
            w.model_copy(update={"start": round(LEAD + w.start, 3), "end": round(LEAD + w.end, 3)})
            for w in (words or {}).get(item.index, [])
        ]
    spec.duration = round(_frames(end) + (spec.credit.duration if spec.credit else 0.0), 3)
    return spec


class TimingNode(FunctionNode):
    name = "timing"

    def run(self, ctx: RunContext) -> None:
        assert ctx.spec
        if ctx.music and ctx.brief.music:
            ctx.spec.music = ctx.music["file"]
        apply_timing(ctx.spec, ctx.narrated, ctx.brief, ctx.words)
        ctx.events.emit(
            "node.task",
            node=self.name,
            task=f"{len(ctx.spec.scenes)} scenes, {ctx.spec.duration:.1f}s of {ctx.brief.duration}s",
        )
        if ctx.spec.credit is None:  # plan §3.7: the run log says when the visible credit is off
            ctx.events.emit("node.task", node=self.name, task="Visible credit disabled by REELHIVE_DISABLE_CREDIT")
