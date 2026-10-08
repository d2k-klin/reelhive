# `render`

**Overview.** The bridge from Python to the Node renderer. It runs `renderer/render.ts` on a `spec.json`, streams progress back as events, and turns a renderer crash into a readable error.

## What's here

| File | What it is |
| --- | --- |
| [`bridge.py`](bridge.py) | `render(spec, out, on_progress)`: runs `node_modules/.bin/tsx render.ts <spec> <out>` in `renderer/` with `DISABLE_TELEMETRY=true`, parses `progress <0..1>` lines into `on_progress`, and keeps the last 40 output lines for `RenderError`. |

The output is a **silent** MP4. `nodes/render_node.py` then mixes and muxes the audio with `audio/mixer.py`.

## Extending

- **More progress detail:** print more structured lines from `render.ts` and parse them here; keep the `progress` line format stable.
- **Another renderer:** anything with the same signature works. `RunContext.renderer` is injectable, and the tests pass an ffmpeg stand-in (`stub_renderer`).

Tests: `tests/unit/test_mixer_bridge.py` fakes `tsx` with a shell script to check progress parsing and error reporting; `tests/e2e/` runs the real renderer.
