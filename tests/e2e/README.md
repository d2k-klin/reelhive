# `tests/e2e`

**Overview.** The slow, real thing: real Kokoro speech, real Revideo rendering in headless Chrome, real ffmpeg mixing. Marked `@pytest.mark.slow`, so the default suite skips them; they run nightly and with `make test-slow`.

## What's here

| File | Covers |
| --- | --- |
| [`test_render_slow.py`](test_render_slow.py) | One short scene with Kokoro voice, library music and the end credit; checks duration, 1920×1080, audio stream, progress and the metadata tag |
| [`test_visual_render_slow.py`](test_visual_render_slow.py) | Portrait and square renders with brand colors and logo, browser and phone frames, a panning screenshot and wrapped copy |

```bash
make test-slow
```

Needs the Kokoro model (downloaded from Hugging Face on first use), `chrome-headless-shell` (`npx puppeteer browsers install chrome-headless-shell`) and the renderer's `npm ci`. On macOS the repo's absolute path must be short enough for espeak-ng's data path (deeply nested temp folders can fail with `phontab: No such file`).

## Extending

Keep these few and short: each adds real seconds to the nightly run. Add one when a template, frame, format or audio behaviour can only be verified by rendering. Assert with `mixer.probe()` (duration, size, streams, tags) and, for layout, sample a frame with ffmpeg.
