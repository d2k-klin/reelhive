# `server`

**Overview.** The local web API behind `reelhive ui`: a FastAPI app that serves the React studio and exposes the same operations as the CLI, through `core/workspace.py` and `core/service.py`. It is built to be safe on a developer's machine: loopback only, a secret launch token, and Host and Origin checks on every request.

## What's here

| File | What it is |
| --- | --- |
| [`app.py`](app.py) | `create_app()`: every `/api/...` route (health, doctor, settings, providers, voices preview, music, brief validate, import and export, runs: create, start, approve, regenerate (with an optional quick-action `suggestion` label), undo, edit spec, cancel, resume, events (SSE, resumable by event id), files, bundle, uploads, capture test, login), plus serving the built UI. `serve()` binds 127.0.0.1 on a free port and prints the tokenised URL. |
| [`agui.py`](agui.py) | M6: `POST /api/agui/suggest`, an AG-UI endpoint that streams one `propose_suggestions` tool call built from `Service.suggest()` (validated, cached, logged). CopilotKit renders it as buttons. Mounted inside the app, so it gets the same security middleware. |
| [`security.py`](security.py) | `protect()`: rejects foreign `Host`, requires the launch token (`Authorization: Bearer` or `?token=` for EventSource), requires a same-origin `Origin` on writes, caps request bodies at 11 MB, sets `no-referrer`, `nosniff` and `no-store`. `validate_host()` refuses any bind address but 127.0.0.1. |

## Extending: a new route

1. Put the behaviour in `core/service.py` (or `core/workspace.py` if it's about jobs and files), so the CLI can use it too.
2. Add a thin route in `create_app()` with Pydantic request and response models; raise `ValueError` for bad input (it becomes a 422).
3. Regenerate the UI's types: `uv run python scripts/generate_ui.py`.
4. Test it in `tests/unit/test_server.py`, including that it rejects a missing token and a foreign Origin. The security middleware covers every `/api` route automatically; don't add routes outside `/api` for data.
