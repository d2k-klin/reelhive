# `core`

**Overview.** The heart of a run: the service that starts, pauses, resumes and reports runs; the `RunContext` every node reads and writes; and the event stream that feeds the terminal, the UI and `run.log.jsonl`. The CLI (and the M3 UI) are thin layers over this folder, so a feature added here lands in both.

## What's here

| File | What it is |
| --- | --- |
| [`service.py`](service.py) | `Service`: `run` (draft graph, then production or an approval stop), `approve` (after the script), `approve_scenes` (after the high-level scene stop), `save_script` / `save_spec` (edits), `regenerate_script` / `regenerate_scene` (with a note), `preview_scene`, `cancel`, `resume` (from the last checkpoint), `suggest` (M6), `undo_script` / `undo_scene`. Before a regeneration, the previous beat or scene is pushed onto `runs/<run>/versions/` (`push_version` / `pop_version`) so it can be undone; applying a quick action emits `suggestion.applied`, undo emits `version.restored`. Creates the run folder, writes `status.json` and `config.json`, and emits `node.skipped` / `run.finished`. `spec_only` and `image_generator` exist for evals. |
| [`workspace.py`](workspace.py) | `Workspace`: what the UI server calls. Wraps `Service` with a job queue (one production at a time), run listing (`RunView`), uploads (capped, re-encoded), file and bundle downloads (allow-listed), screenshot tests, the login flow, delete and reveal. |
| [`context.py`](context.py) | `RunContext`: run folder, brief, config, models, TTS, renderer, and the typed state nodes share (`script`, `spec`, `narrated`, `voiced`, `music`, `failures`, `critic_passed`, ...). Passed to nodes through Strands' `invocation_state`. `checkpoint()` / `restore()` save completed nodes so `resume` can continue after a crash or cancel. |
| [`events.py`](events.py) | `EventBus` (fan out to subscribers, append to `run.log.jsonl`, thread-safe), the closed list of event types, and `replay()` to read a log back. |

## Run states (`status.json`)

`queued` → `drafting` → `awaiting_script` (medium, high) → `producing` → `awaiting_scenes` (high) → `producing` → `done`.
Side states: `editing` / `regenerating` (high edits), `stopped` (hard checks still failing after `fix`), `failed` (an exception), `cancelled`, `interrupted` (resume continues from the checkpoint).

## Extending

- **New event:** add its name to `EVENT_TYPES` in `events.py` (emitting an unknown type raises), emit it from the node or service, and handle it in `_printer` in `cli.py`. Document it in [docs/architecture.md](../../../docs/architecture.md#events).
- **New shared state:** add a field to `RunContext` with a default, and make sure only one node writes it per phase (parallel branches run at the same time).
- **New run operation** (regenerate, cancel, resume...): add a `Service` method; the CLI and UI call it. Reuse `_dependencies()` and `_context()` to rebuild a context from a run folder, as `approve` does.

## Testing

`tests/integration/test_graphs.py` and `test_medium.py` drive `Service` end to end with `FakeModel`, `StubTTS` and `stub_renderer`; `tests/unit/test_infra.py` covers events and replay.
