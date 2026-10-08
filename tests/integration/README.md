# `tests/integration`

**Overview.** End-to-end runs of the real graphs and service with fakes at the edges (`FakeModel`, `StubTTS`, `stub_renderer`). These prove the pipeline's behaviour: which nodes run, in what order, which path is taken, and what lands in the run folder.

## What's here

| File | Covers |
| --- | --- |
| [`test_graphs.py`](test_graphs.py) | The pass path (parallel branches, events, run folder, video with the metadata tag), the hard-check → `fix` → `recheck` path, the stop-with-report path, a critic rejection, the credit env switch, node errors failing the run |
| [`test_medium.py`](test_medium.py) | Medium pauses after the script, resumes from an edited `script.json` in 9:16 and 1:1 with brand colors, refuses invalid or double approval, keeps the lock rules |
| [`test_high.py`](test_high.py) | High pauses after the script and again after the scenes, then renders; a per-scene voice override is used |
| [`test_eval_run.py`](test_eval_run.py) | `reelhive eval` on the smoke set: two fake providers (one good, one that drops features) through the real graphs, fixture-site screenshots, the judge, reports, the gate, no video |

## Extending

When you change what the graph does (a new node, a new condition, a new pause), add or extend a scenario here. Assert on **events** (`node.started` order, `gate.result`, `node.skipped`) and on the **run folder**: they're what the CLI and UI rely on. `test_eval_run.py` shows how to write a fake that answers per brief (`BriefAwareFake`) when one model serves many runs at once.
