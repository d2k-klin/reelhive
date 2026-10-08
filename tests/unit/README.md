# `tests/unit`

**Overview.** Fast, focused tests: one module, contract or rule per file. Most run in milliseconds and need nothing but Python.

## What's here

| File | Covers |
| --- | --- |
| [`test_schemas.py`](test_schemas.py) | Brief validation and rejections; planner template limits; mapping planner fields onto template text |
| [`test_timing.py`](test_timing.py) | Padding to the target, the padding cap, tail trimming, the credit rule and env switch, short-video word targets |
| [`test_checks.py`](test_checks.py) | Every hard check passing and failing |
| [`test_contract.py`](test_contract.py) | Committed `spec.schema.json` equals the Pydantic export; the credit text matches the renderer constant |
| [`test_mixer_bridge.py`](test_mixer_bridge.py) | ffmpeg argument building (ducking, looping, metadata), voice placement, ffmpeg errors, renderer progress parsing and failures |
| [`test_infra.py`](test_infra.py) | Events and replay, config loading, levels, the provider factory, the music manifest and track choice, doctor's credit status |
| [`test_providers.py`](test_providers.py) | Every provider's model wiring, per-node overrides, the Copilot node (submit, repair, streaming, denied permissions, cleanup) via `FakeCopilotSession`, the OpenAI image generator, Strands repair |
| [`test_visuals.py`](test_visuals.py) | The visual source matrix and fallbacks, generation cache and cap, resolution and path gates, theme and logo, catalog shortcuts, cross-origin rejection, opt-in image descriptions |
| [`test_login.py`](test_login.py) | `reelhive login` saves state with owner-only permissions and closes the browser |
| [`test_evals.py`](test_evals.py) | The eval dataset covers the plan's matrix; TTS estimate, prompt recorder, fixture site; aggregation, the 5% gate, reports |
| [`test_suggester.py`](test_suggester.py) | M6 suggestions: validation, cache per version, events, scene vs beat, provider limits |
| [`test_server.py`](test_server.py) | The local API rejects a missing token, a foreign Host and Origin; run files and SSE replay stay inside the workspace; loopback-only binding |
| [`test_design.py`](test_design.py) | Design prompts compose with the shared style and reference; every node has a role-portrait prompt; dry run |
| [`test_docs.py`](test_docs.py) | Every relative link in every README and doc resolves; every project folder has a README; demo assets exist |

## Extending

Name the file after the module or rule (`test_<thing>.py`), and the test after the behaviour (`test_padding_is_capped_so_...`). Prefer one assertion per idea and real objects over mocks; reach for `monkeypatch` only at process or network boundaries.
