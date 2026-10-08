# `audio/tts`

**Overview.** Text-to-speech behind one tiny interface, so the engine can change without touching the graph. Kokoro-82M is the default: local, Apache-2.0, runs on CPU, Apple Silicon or CUDA.

## What's here

| File | What it is |
| --- | --- |
| [`base.py`](base.py) | `TTS` protocol: `synth(text, out, gender, accent, speed) -> seconds`. Writes a WAV and returns its real length, which `timing` uses. |
| [`kokoro.py`](kokoro.py) | `KokoroTTS`: lazy-loads torch and Kokoro (US and UK pipelines), maps gender and accent to voices (`af_heart`, `bf_emma`, `am_michael`, `bm_george`), writes 24 kHz mono WAV. |

Kokoro speaks about 161 words per minute at speed 1.0 (measured; `SPEECH_WPM` in `nodes/timing_node.py`). The script's word target and the eval stand-in both depend on it.

## Extending: a new engine (e.g. Piper for German)

1. Add `piper.py` with a class implementing `synth`. Write 24 kHz mono WAV (the mixer expects 24 kHz) and return the duration in seconds.
2. Choose the engine in `Service._dependencies()` (or from config) based on the brief's language.
3. Measure its words per minute and make `SPEECH_WPM` engine-aware, or videos will come out too long or too short.
4. Add a slow test like `tests/e2e/test_render_slow.py`.

Tests never load Kokoro: they use `StubTTS` (`tests/conftest.py`) and the evals use `EstimateTTS` (`evals/harness.py`).
