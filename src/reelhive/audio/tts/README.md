# `audio/tts`

**Overview.** Text-to-speech behind one tiny interface, so the engine can change without touching the graph. Kokoro-82M is the default: local, Apache-2.0, runs on CPU, Apple Silicon or CUDA.

## What's here

| File | What it is |
| --- | --- |
| [`base.py`](base.py) | `TTS` protocol: `synth(text, out, gender, accent, speed) -> Speech`. Writes a WAV and returns its real length (which `timing` uses) and its words with their times (which captions use). `estimate_words()` spreads words over the audio for engines without timestamps. `trim_silence()` / `shift_words()` cut the silence an engine pads a clip with and move the word times to match, so a clip's length is its speech and timing's own pauses (`LEAD`, `TAILS`) are the only gaps. |
| [`kokoro.py`](kokoro.py) | `KokoroTTS`: lazy-loads torch and Kokoro (US and UK pipelines), maps gender and accent to voices (`af_heart`, `bf_emma`, `am_michael`, `bm_george`), writes 24 kHz mono WAV trimmed to the speech (Kokoro pads every clip with about 0.3 s before and 0.5 s after). `chunk_words()` joins Kokoro's per-token timestamps across chunks, punctuation attached to its word. |

Kokoro speaks about 145 words per minute at speed 1.0 on real product scripts with names and numbers, clips trimmed (measured 138-154; about 161 on plain sentences; `SPEECH_WPM` in `nodes/timing_node.py`). The script's word target and the eval stand-in both depend on it.

## Extending: a new engine (e.g. Piper for German)

1. Add `piper.py` with a class implementing `synth`. Write 24 kHz mono WAV (the mixer expects 24 kHz) and return a `Speech`: the duration, and word timings if the engine reports them (otherwise `estimate_words()`).
2. Choose the engine in `Service._dependencies()` (or from config) based on the brief's language.
3. Measure its words per minute and make `SPEECH_WPM` engine-aware, or videos will come out too long or too short.
4. Add a slow test like `tests/e2e/test_render_slow.py`.

Tests never load Kokoro: they use `StubTTS` (`tests/conftest.py`) and the evals use `EstimateTTS` (`evals/harness.py`).
