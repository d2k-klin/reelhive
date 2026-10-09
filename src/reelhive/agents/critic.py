"""Hard checks (plan §3.3) plus an LLM rubric review."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from strands.types.event_loop import Usage

from reelhive.agents.plan import brief_block, research_block
from reelhive.core.context import RunContext
from reelhive.nodes.base import AgentNode, _no_usage
from reelhive.schemas.brief import Brief
from reelhive.schemas.scene_spec import SceneSpec

DURATION_TOLERANCE = 0.05
WPM_RANGE = (130, 170)


@dataclass
class Check:
    name: str
    value: Any
    threshold: str
    passed: bool
    message: str = ""


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def voice_wpm(spec: SceneSpec, narrated: dict[int, tuple[str, float]]) -> float:
    """How fast this voice actually speaks this script: spoken words per minute of speech."""
    words = sum(len(narrated[s.index][0].split()) for s in spec.scenes if s.index in narrated)
    seconds = sum(narrated[s.index][1] for s in spec.scenes if s.index in narrated)
    return words / seconds * 60 if seconds > 0 else WPM_RANGE[0]


def hard_checks(
    spec: SceneSpec, brief: Brief, narrated: dict[int, tuple[str, float]], run_dir: Path | None = None
) -> list[Check]:
    checks = []

    err = (spec.duration - brief.duration) / brief.duration
    checks.append(
        Check(
            "duration",
            round(spec.duration, 2),
            f"{brief.duration}s ±5%",
            abs(err) <= DURATION_TOLERANCE,
            f"video is {spec.duration:.1f}s for a {brief.duration}s target ({err:+.0%})",
        )
    )

    # Notes are topics, not copy: a note counts as covered when some scene says it tells it (`covers`).
    told = {n for s in spec.scenes for n in s.covers}
    missing = [f"{i}. {note}" for i, note in enumerate(brief.features, start=1) if i not in told]
    checks.append(
        Check(
            "features",
            f"{len(brief.features) - len(missing)}/{len(brief.features)}",
            "all covered",
            not missing,
            f"key points not told by any scene (set `covers` on the scene that tells each): {missing}",
        )
    )

    words = sum(len(s.narration.split()) for s in spec.scenes)
    credit_seconds = spec.credit.duration if spec.credit else 0
    intro_seconds = spec.intro.duration if spec.intro else 0
    minutes = (spec.duration - credit_seconds - intro_seconds) / 60
    wpm = round(words / minutes) if minutes > 0 else 0
    # The floor catches scripts that leave long silences. A slow voice can't reach 130 wpm of video
    # however the script is cut, so the floor follows the voice's measured rate (a 125-wpm voice once
    # made duration and pace impossible to satisfy together).
    low = min(WPM_RANGE[0], round(0.85 * voice_wpm(spec, narrated))) if narrated else WPM_RANGE[0]
    checks.append(
        Check(
            "pace",
            wpm,
            f"{low}-{WPM_RANGE[1]} wpm",
            low <= wpm <= WPM_RANGE[1],
            f"{words} words over {minutes * 60:.0f}s is {wpm} words per minute",
        )
    )

    try:
        SceneSpec.model_validate(spec.model_dump())
        text_ok, text_msg = True, ""
    except ValidationError as e:
        text_ok, text_msg = False, f"on-screen text too long: {e.errors()[0]['loc']} {e.errors()[0]['msg']}"
    checks.append(Check("text_limits", text_ok, "within template limits", text_ok, text_msg))

    stale = [s.index for s in spec.scenes if narrated.get(s.index, ("",))[0] != s.narration]
    checks.append(Check("audio", not stale, "every scene voiced", not stale, f"scenes without matching audio: {stale}"))
    from reelhive.visuals.resolver import image_ok, local_asset

    bad_images, generated_ui = [], []
    for scene in spec.scenes:
        if scene.visual_request.kind == "product_ui" and scene.visual and scene.visual.source == "generated":
            generated_ui.append(scene.index)
        if scene.visual:
            try:
                valid = run_dir is not None and image_ok(local_asset(run_dir, scene.visual.file), brief.format)
            except ValueError:
                valid = False
            if not valid:
                bad_images.append(scene.index)
        elif scene.template in ("image-full", "screenshot-pan"):
            bad_images.append(scene.index)
    checks.append(
        Check(
            "images",
            not bad_images,
            "files exist and meet minimum resolution",
            not bad_images,
            f"missing, invalid or low-resolution images: {bad_images}",
        )
    )
    checks.append(
        Check(
            "product_ui",
            not generated_ui,
            "no generated product UI",
            not generated_ui,
            f"generated images in product UI scenes: {generated_ui}",
        )
    )
    clipped = [s.index for s in spec.scenes if s.duration < narrated.get(s.index, ("", 0))[1] + 0.3]
    checks.append(
        Check(
            "voice_fit", not clipped, "narration fits scene", not clipped, f"scene duration clips narration: {clipped}"
        )
    )
    if brief.level == "high":
        unapproved = [s.index for s in spec.scenes if s.visual and not s.image_approved]
        checks.append(
            Check(
                "image_approval",
                not unapproved,
                "all images approved",
                not unapproved,
                f"images need approval: {unapproved}",
            )
        )
    return checks


def run_gates(ctx: RunContext, node: str) -> list[str]:
    """Run the hard checks, emit one gate.result per check, return failure messages."""
    assert ctx.spec
    failures = []
    for c in hard_checks(ctx.spec, ctx.brief, ctx.narrated, ctx.run_dir):
        ctx.events.emit("gate.result", node=node, check=c.name, value=c.value, threshold=c.threshold, passed=c.passed)
        if not c.passed:
            failures.append(c.message)
    return failures


def scenes_block(spec: SceneSpec, narrated: dict[int, tuple[str, float]]) -> str:
    lines = []
    if spec.intro:
        shown = spec.intro.model_dump_json(exclude_none=True, exclude={"duration"})
        lines.append(f"Intro screen ({spec.intro.duration:.0f}s, no narration): {shown}")
    for s in spec.scenes:
        speech = narrated.get(s.index, ("", 0.0))[1]
        lines.append(
            f"Scene {s.index} [{s.template}] {s.duration:.1f}s (speech {speech:.1f}s), "
            f"covers={s.covers}\n  text: {s.text.model_dump_json(exclude_none=True)}\n"
            f"  narration: {s.narration}\n  visual request: {s.visual_request.model_dump_json()}"
        )
    return "\n".join(lines)


class Verdict(BaseModel):
    hook: int = Field(ge=1, le=5)
    clarity: int = Field(ge=1, le=5)
    audience_fit: int = Field(ge=1, le=5)
    storyline: int = Field(ge=1, le=5)
    cta: int = Field(ge=1, le=5)
    passed: bool
    reasons: list[str] = Field(default_factory=list, description="Concrete fixes needed when not passed")


class CriticNode(AgentNode):
    name = "critic"
    tier = "strong"
    prompt = "critic"
    output = Verdict

    async def execute(self, ctx: RunContext) -> Usage:
        ctx.failures = run_gates(ctx, self.name)
        if ctx.failures:  # hard checks failed: go straight to `fix`, no LLM call
            ctx.critic_passed = False
            return _no_usage()
        return await super().execute(ctx)

    def build_prompt(self, ctx: RunContext) -> str:
        assert ctx.spec
        return f"{brief_block(ctx.brief)}{research_block(ctx)}\n\nScenes:\n{scenes_block(ctx.spec, ctx.narrated)}"

    def apply(self, ctx: RunContext, out: Verdict) -> None:
        scores = out.model_dump(exclude={"passed", "reasons"})
        passed = out.passed and min(scores.values()) >= 3
        ctx.events.emit("critic.verdict", node=self.name, scores=scores, passed=passed, reasons=out.reasons)
        ctx.critic_passed = passed
        ctx.failures = [] if passed else (out.reasons or ["critic rubric score below 3"])
