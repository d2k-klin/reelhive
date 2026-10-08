"""Hard checks (plan §3.3) plus an LLM rubric review."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from strands.types.event_loop import Usage

from reelhive.agents.plan import brief_block
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

    last = spec.scenes[-1]
    on_screen = [v for v in last.text.model_dump().values() if v]
    closing = _norm(brief.closing)
    found = any(closing in _norm(t) for t in [last.narration, *on_screen])
    checks.append(
        Check(
            "closing",
            found,
            "verbatim in final scene",
            found,
            f"final scene must contain the closing message verbatim: {brief.closing!r}",
        )
    )

    def covered(feature: str) -> bool:
        return any(
            _norm(s.feature or "") == _norm(feature) or _norm(feature) in _norm(s.narration) for s in spec.scenes
        )

    missing = [f for f in brief.features if not covered(f)]
    checks.append(
        Check(
            "features",
            f"{len(brief.features) - len(missing)}/{len(brief.features)}",
            "all covered",
            not missing,
            f"features not covered by any scene: {missing}",
        )
    )

    words = sum(len(s.narration.split()) for s in spec.scenes)
    minutes = (spec.duration - (spec.credit.duration if spec.credit else 0)) / 60
    wpm = round(words / minutes) if minutes > 0 else 0
    checks.append(
        Check(
            "pace",
            wpm,
            f"{WPM_RANGE[0]}-{WPM_RANGE[1]} wpm",
            WPM_RANGE[0] <= wpm <= WPM_RANGE[1],
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
    for s in spec.scenes:
        speech = narrated.get(s.index, ("", 0.0))[1]
        lines.append(
            f"Scene {s.index} [{s.template}] {s.duration:.1f}s (speech {speech:.1f}s), "
            f"feature={s.feature!r}\n  text: {s.text.model_dump_json(exclude_none=True)}\n"
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
        return f"{brief_block(ctx.brief)}\n\nScenes:\n{scenes_block(ctx.spec, ctx.narrated)}"

    def apply(self, ctx: RunContext, out: Verdict) -> None:
        scores = out.model_dump(exclude={"passed", "reasons"})
        passed = out.passed and min(scores.values()) >= 3
        ctx.events.emit("critic.verdict", node=self.name, scores=scores, passed=passed, reasons=out.reasons)
        ctx.critic_passed = passed
        ctx.failures = [] if passed else (out.reasons or ["critic rubric score below 3"])
