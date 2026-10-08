# `tests`

**Overview.** The pytest suite. The default run needs **no API keys, no internet and no Kokoro model**: agents run on fakes, TTS writes silence, the renderer is replaced by ffmpeg, and screenshots hit a site served on 127.0.0.1. Real-model and real-render checks are marked `slow`.

## What's here

| Path | Layer | Runs |
| --- | --- | --- |
| [`conftest.py`](conftest.py) | Shared fakes and fixtures: `FakeModel` (a Strands model that answers structured-output calls with canned JSON keyed by output class name), `StubTTS`, `stub_renderer`, `make_script` / `make_plan` / `words`, the `brief` and `config` fixtures | – |
| [`unit/`](unit) | One module or contract at a time | every push |
| [`integration/`](integration) | Whole graphs and the eval harness with fakes | every push |
| [`capture/`](capture) | Real headless Chromium against a local fixture site | every push |
| [`e2e/`](e2e) | Real Kokoro, real Revideo, real ffmpeg (`@pytest.mark.slow`) | nightly, `make test-slow` |

```bash
make test          # unit + integration + capture, coverage gate 85%, plus renderer vitest
make test-slow     # the e2e layer
uv run pytest tests/unit/test_timing.py -q   # one file
```

## Extending

- **Put a test in the lowest layer that can catch the bug.** A pure function goes in `unit/`; a change in what the graph does goes in `integration/`; a real render or real TTS goes in `e2e/` with `pytestmark = pytest.mark.slow`.
- **Need an LLM answer?** Use `FakeModel({"OutputClassName": {...}})`. A list value is consumed in order, which is useful for the fix path. Asking for a name that isn't there fails loudly, which is how tests prove an agent was *not* called.
- **No network.** Anything that would reach the internet must be faked or served locally (see the site fixture in `capture/test_capture.py`).
- The suite imports `evals` from the repo root (`pythonpath = ["."]` in `pyproject.toml`).
