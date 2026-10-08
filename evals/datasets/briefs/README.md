# `evals/datasets/briefs`

**Overview.** The 24 briefs the evals run. Each is a normal ReelHive brief, chosen to cover a different corner: technical and non-technical audiences, 15 s to 3 min, all three formats, 1 to 8 features, closings with URLs and numbers, `small` and `medium`, and every combination of visual sources.

## Naming

`<topic>-<seconds>.yaml`, e.g. `bakery-15.yaml` or `security-180.yaml`. A few are named for the edge case they test (`numbers-closing-40`, `url-closing-25`).

## Adding a brief

1. Copy the closest brief and change it. Use `${DATASET}/images` and `${SITE}` for visual sources; never real URLs, because evals must not touch the internet.
2. Add its name to `core` in [`../sets.yaml`](../sets.yaml) (and to `smoke` only if it replaces one there; smoke stays at 5).
3. Check it validates: `uv run pytest tests/unit/test_evals.py`.
4. Refresh the baseline (`make eval-baseline`) in the same PR.

Fictional products only. These briefs end up in reports and prompts.
