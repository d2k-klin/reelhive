"""`reelhive eval`: run every brief of a set through each provider, score it, report and gate (plan §7).

Runs the real draft and production graphs in spec-only mode: TTS is an estimate, nothing is rendered,
images are placeholders (prompts are recorded and judged), screenshots come from a local fixture site.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from strands.models.model import Model

from evals.harness import DATASET, EstimateTTS, PromptRecorder, load_set, serve_site
from evals.metrics.deterministic import node_stats, score_spec
from evals.metrics.judge import judge_run
from reelhive.config import Config
from reelhive.core.events import Event
from reelhive.core.service import Service
from reelhive.schemas.brief import Brief

# (key, label, higher_is_better). Only higher-is-better metrics are gated; None means informational.
METRICS: list[tuple[str, str, bool | None]] = [
    ("success", "Reached render", True),
    ("schema_first_try", "Schema valid on first try", True),
    ("fix_iterations", "Fix iterations (mean)", None),
    ("duration_ok", "Duration within ±5%", True),
    ("duration_error_pct", "Duration error % (mean)", None),
    ("closing_match", "Closing message exact match", True),
    ("feature_coverage", "Feature coverage", True),
    ("pace_ok", "Pace 130-170 wpm", True),
    ("wpm", "Words per minute (mean)", None),
    ("text_fit", "No text overflow", True),
    ("text_overflow", "Text-overflow violations (mean)", None),
    ("visual_coverage", "Visual coverage (when a source exists)", True),
    ("product_ui_generated", "Generated images in product UI (must be 0)", None),
    ("judge_hook", "Judge: hook strength (1-5)", True),
    ("judge_clarity", "Judge: clarity (1-5)", True),
    ("judge_audience_fit", "Judge: audience fit (1-5)", True),
    ("judge_storyline", "Judge: storyline adherence (1-5)", True),
    ("judge_cta", "Judge: call to action (1-5)", True),
    ("judge_prompt_relevance", "Judge: image prompt relevance (1-5)", True),
    ("judge_prompt_style", "Judge: image prompt style consistency (1-5)", True),
    ("judge_prompt_no_product_ui", "Judge: image prompts avoid product UI (1-5)", True),
    ("image_count", "Images per brief (placeholders)", None),
    ("tokens", "Tokens per brief", None),
    ("seconds", "Wall time per brief (s)", None),
]
TOLERANCE = 0.05  # prompt changes may not drop a gated metric by more than 5% (relative)


async def eval_brief(
    provider: str, name: str, brief: Brief, config: Config, models: dict[str, Model], judge: Model | None
) -> dict[str, Any]:
    events: list[Event] = []
    service = Service(config, models, EstimateTTS(), spec_only=True, image_generator=PromptRecorder())
    ctx = service.new_run(brief, events.append)
    record: dict[str, Any] = {"provider": provider, "brief": name, "run_dir": str(ctx.run_dir)}
    started = time.time()
    try:
        result = await service.run_async(ctx)
        if result.status == "awaiting_script":  # medium briefs: evals approve the draft as written
            result = await service.run_async(ctx, approved=True)
        record["outcome"] = result.status
    except Exception as e:
        record["outcome"], record["error"] = "failed", f"{type(e).__name__}: {e}"
    record["success"] = record["outcome"] == "done"
    record.update(node_stats(events))
    record["seconds"] = round(time.time() - started, 2)
    if ctx.spec and ctx.narrated:
        record.update(score_spec(ctx.spec, ctx.brief, ctx.narrated, ctx.run_dir))
    if judge and ctx.script:
        try:
            record.update(await judge_run(judge, ctx.brief, ctx.script, ctx.spec))
        except Exception as e:
            record["judge_error"] = f"{type(e).__name__}: {e}"
    return record


def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {"briefs": len(records)}
    for key, _, _ in METRICS:
        values = [float(r[key]) for r in records if r.get(key) is not None]
        out[key] = round(sum(values) / len(values), 4) if values else None
    for field in ("node_seconds", "node_tokens"):
        per_node: dict[str, list[float]] = {}
        for r in records:
            for node, value in r.get(field, {}).items():
                per_node.setdefault(node, []).append(value)
        out[field] = {node: round(sum(v) / len(records), 2) for node, v in per_node.items()}
    return out


def gate(current: dict[str, dict[str, Any]], baseline: dict[str, dict[str, Any]]) -> list[str]:
    """Regressions of more than 5% against the baseline, plus any generated product UI."""
    problems = []
    for provider, now in current.items():
        if provider not in baseline:
            problems.append(f"{provider}: no baseline; run with --save-baseline first")
            continue
        if now.get("product_ui_generated"):
            problems.append(f"{provider}: generated images in product UI scenes ({now['product_ui_generated']})")
        for key, label, higher in METRICS:
            before, after = baseline[provider].get(key), now.get(key)
            if higher and before is not None and after is not None and after < before * (1 - TOLERANCE):
                problems.append(f"{provider}: {label} fell from {before:g} to {after:g} (more than 5%)")
    return problems


async def run_eval_async(
    providers: list[str],
    config: Config,
    set_name: str = "core",
    judge: Model | None = None,
    out_dir: Path = Path("evals/reports"),
    models_for: Callable[[str], dict[str, Model]] | None = None,
    concurrency: int = 4,
    dataset: Path = DATASET,
) -> dict[str, Any]:
    from reelhive.providers.factory import build_models

    stamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    report_dir = out_dir / f"{stamp}_{set_name}"
    configs = {p: config.model_copy(update={"provider": p, "runs_dir": report_dir / "runs" / p}) for p in providers}
    # Fail fast on a misconfigured provider before spending anything.
    models = {p: (models_for or (lambda p: build_models(configs[p])))(p) for p in providers}
    limit = asyncio.Semaphore(concurrency)
    with serve_site() as site:
        briefs = load_set(set_name, site, dataset)

        async def one(provider: str, name: str, brief: Brief) -> dict[str, Any]:
            async with limit:
                return await eval_brief(provider, name, brief, configs[provider], models[provider], judge)

        records = await asyncio.gather(*(one(p, n, b) for p in providers for n, b in briefs.items()))
    report = {
        "set": set_name,
        "created": stamp,
        "briefs": list(briefs),
        "judge": judge is not None,
        "providers": {p: aggregate([r for r in records if r["provider"] == p]) for p in providers},
        "records": records,
        "dir": str(report_dir),
    }
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "results.json").write_text(json.dumps(report, indent=2, default=str))
    from evals.report import write_reports

    write_reports(report, report_dir)
    return report
