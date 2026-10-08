---
name: ffmpeg-media
description: "Build, debug, or test audio/video processing with ffmpeg and ffprobe, including mixing, normalization, sidechain ducking, stream mapping, metadata, duration checks, subprocess safety, and cross-platform binary discovery. Use for media pipelines or render post-processing."
---

# ffmpeg Media Pipelines

Use this workflow for deterministic media post-processing.

## Procedure

1. Discover `ffmpeg` and `ffprobe` explicitly and report their versions. If using bundled fallbacks, keep discovery in one module.
2. Build argument arrays, never shell command strings. Treat every file path and metadata value as untrusted.
3. Probe all inputs before processing and validate expected streams, codecs, durations, sample rates, and channel layouts.
4. Normalize inputs to compatible audio/video characteristics before mixing or concatenation.
5. Make stream mapping explicit. Do not rely on ffmpeg's automatic stream selection in production workflows.
6. For narration over music, use measured levels and sidechain compression/ducking with documented attack, release, threshold, and makeup gain.
7. Write to a temporary output, probe it, then atomically move it into place.
8. Capture stderr, exit status, elapsed time, and the sanitized argument list. Support cancellation and terminate child processes cleanly.

## Validation

- Use `ffprobe` JSON output through a structured parser.
- Check output existence, nonzero size, expected streams, dimensions, duration tolerance, and required metadata.
- Detect clipping and unexpected silence where audio quality matters.

## Testing

- Unit test argument construction and binary fallback logic.
- Generate tiny synthetic fixtures for integration tests.
- Cover paths with spaces, missing streams, corrupt input, cancellation, and metadata escaping.

## Done When

Commands are injection-safe, stream selection is explicit, outputs are probed before publication, and failures include actionable ffmpeg diagnostics.