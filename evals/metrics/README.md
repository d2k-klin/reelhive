# `evals/metrics`

**Overview.** How an eval run is scored. Deterministic metrics come straight from the run (no LLM); judge metrics come from one fixed judge model with written rubrics, so every provider is graded the same way.

## What's here

| File | What it is |
| --- | --- |
| [`deterministic.py`](deterministic.py) | `node_stats(events)`: seconds and tokens per node, first-try schema validity, fix iterations, image count and cost. `score_spec(spec, brief, narrated, run_dir)`: the critic's hard checks as scores (duration error, closing match, feature coverage, pace, text overflow, visual coverage, generated product UI). |
| [`judge.py`](judge.py) | `judge_run(model, brief, script, spec)`: scores the script (hook, clarity, audience fit, storyline, CTA) and every concept image prompt (relevance, style, no product UI) from 1 to 5, using `../rubrics/`. |

## Extending: a new metric

1. Compute it in `deterministic.py` (preferred) or `judge.py`, returning a number or a bool per run (or `None` when it doesn't apply).
2. Add `(key, label, higher_is_better)` to `METRICS` in [`../run.py`](../run.py). `True` makes it part of the 5% gate, and `None` makes it informational.
3. Cover it in `tests/unit/test_evals.py` and refresh the baseline.

Prefer deterministic metrics: they're free, stable, and explainable.
