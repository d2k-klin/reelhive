# `evals/datasets`

**Overview.** The fixed inputs every eval run uses: the briefs, which briefs form each set, and the local images and website that visual briefs point to. Keeping them fixed is what makes runs comparable over time and across providers.

## What's here

| Path | What it is |
| --- | --- |
| [`briefs/`](briefs) | 24 ordinary ReelHive briefs covering the plan's matrix |
| [`sets.yaml`](sets.yaml) | `core` (all briefs, used by the gate) and `smoke` (5 briefs, used nightly) |
| [`images/`](images) | Four 1920×1920 fixture images plus `captions.yaml`, for `images` briefs |
| [`site/`](site) | A four-page static app, served on 127.0.0.1 during a run, for `screenshots` briefs |

Briefs use `${DATASET}` and `${SITE}` placeholders; `evals/harness.py` (`load_set`) fills them in and validates each brief like any user brief.

## Extending

Changing anything here changes the baseline. Refresh it in the same PR (`make eval-baseline`) and say why. Keep the core set at 20-30 briefs; `tests/unit/test_evals.py` checks that it still covers every format, 15 s to 180 s, 1 to 8 features, URL and number closings, both levels, and every visual source combination.
