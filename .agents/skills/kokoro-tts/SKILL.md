---
name: kokoro-tts
description: "Build, tune, debug, or test local text-to-speech pipelines with Kokoro, Misaki, PyTorch, and soundfile. Use for voice selection, accents, pronunciation, chunking, speed control, WAV output, duration measurement, model caching, CPU/GPU behavior, and TTS test doubles."
---

# Kokoro TTS

Use this workflow for local speech generation with Kokoro.

## Procedure

1. Confirm the supported Python, Kokoro, Misaki, PyTorch, and language-model versions before changing dependencies.
2. Put Kokoro behind a small TTS interface that accepts text, voice, speed, and output format and returns the actual audio path and measured duration.
3. Normalize text deliberately. Preserve meaningful punctuation, numbers, URLs, and acronyms; add pronunciation overrides at one boundary.
4. Split long input at semantic boundaries and retain deterministic ordering. Avoid chunks so short that prosody becomes discontinuous.
5. Load models once per process and make device selection explicit. Provide a CPU path even when acceleration is available.
6. Write a lossless intermediate such as PCM WAV. Measure duration from the generated file rather than estimating from text.
7. Record voice, speed, sample rate, duration, and generation time without logging sensitive narration unnecessarily.

## Audio Quality Checks

- Reject empty, clipped, non-finite, or implausibly short output.
- Keep sample rate and channel layout consistent across chunks.
- Join chunks with controlled silence or crossfades; do not concatenate incompatible formats.
- Evaluate pronunciation and pace with representative fixtures, not only a hello-world sentence.

## Testing

- Use a fast fake TTS implementation for unit and graph tests.
- Test chunk ordering, duration propagation, cache keys, invalid voices, and device fallback.
- Keep real Kokoro synthesis in a marked slow test with a short fixed sentence.

## Done When

The pipeline is reproducible, model loading is amortized, downstream timing uses measured audio, and ordinary tests do not load model weights.