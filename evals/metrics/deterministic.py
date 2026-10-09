"""The critic's hard checks (plan §3.3) turned into per-run scores. No LLM involved."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from reelhive.agents.critic import hard_checks
from reelhive.core.events import Event
from reelhive.schemas.brief import Brief
from reelhive.schemas.scene_spec import SceneSpec


def node_stats(events: list[Event]) -> dict[str, Any]:
    seconds: dict[str, float] = defaultdict(float)
    tokens: dict[str, int] = defaultdict(int)
    for e in events:
        if e.type == "node.finished":
            seconds[e.data["node"]] += e.data.get("seconds", 0.0)
            tokens[e.data["node"]] += e.data.get("tokens") or 0
    tasks = [e.data for e in events if e.type == "node.task"]
    generated = [t for t in tasks if t["task"].startswith("Generated image")]
    return {
        "node_seconds": dict(seconds),
        "node_tokens": dict(tokens),
        "seconds": round(sum(seconds.values()), 2),
        "tokens": sum(tokens.values()),
        # Strands retries invalid output inside one call; a "Repairing" task means it still failed after that.
        "schema_first_try": not any(t["task"].startswith("Repairing") for t in tasks),
        "fix_iterations": sum(1 for e in events if e.type == "node.started" and e.data["node"] == "fix"),
        "image_count": len(generated),
        "image_cost_usd": sum(t.get("cost_usd") or 0.0 for t in generated) or None,
    }


def has_visual_source(brief: Brief) -> bool:
    v = brief.visuals
    return v.source != "none" and bool(v.screenshots or v.images or v.generate)


def score_spec(spec: SceneSpec, brief: Brief, narrated: dict[int, tuple[str, float]], run_dir: Path) -> dict[str, Any]:
    checks = {c.name: c for c in hard_checks(spec, brief, narrated, run_dir)}
    covered, total = (int(n) for n in str(checks["features"].value).split("/"))
    overflow = 0
    for scene in spec.scenes:
        try:
            type(scene).model_validate(scene.model_dump())
        except ValidationError:
            overflow += 1
    wanting = [s for s in spec.scenes if s.visual_request.kind != "none"]
    return {
        "duration_error_pct": round(abs(spec.duration - brief.duration) / brief.duration * 100, 2),
        "duration_ok": checks["duration"].passed,
        "feature_coverage": covered / total,
        "wpm": checks["pace"].value,
        "pace_ok": checks["pace"].passed,
        "text_overflow": overflow,
        "text_fit": overflow == 0,
        "visual_coverage": (
            sum(1 for s in wanting if s.visual) / len(wanting) if wanting and has_visual_source(brief) else None
        ),
        "product_ui_generated": sum(
            1
            for s in spec.scenes
            if s.visual_request.kind == "product_ui" and s.visual and s.visual.source == "generated"
        ),
        "scenes": len(spec.scenes),
    }
