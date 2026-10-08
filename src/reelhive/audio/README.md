# `audio`

**Overview.** Everything the video sounds like: speech (Kokoro TTS), background music (a curated CC0 library), and the ffmpeg mix that ducks the music under the voice and muxes it into the final MP4.

## What's here

| Path | What it is |
| --- | --- |
| [`tts/`](tts) | Text-to-speech behind a small interface; Kokoro today. |
| [`music_library.py`](music_library.py) | Loads `assets/music/manifest.json`; `pick_track(mood, bpm)` returns the closest tempo within the mood (any mood if none match). |
| [`mixer.py`](mixer.py) | `narration_track()` places each scene's voice on one timeline; `mix_args()` / `mix()` loop and fade the music and duck it with `sidechaincompress`; `mux_args()` / `mux()` add the audio to the silent render and always write the `comment=Made with ReelHive by Mr.D` tag; `probe()` reads duration, streams, size and tags without ffprobe; `ffmpeg_exe()` uses the system ffmpeg or the one bundled with `imageio-ffmpeg`. |

## Extending

- **Different ducking or loudness:** change the filter graph in `mix_args()`. `tests/unit/test_mixer_bridge.py` checks the arguments; listen to a real render (`make test-slow`) before merging.
- **More music:** add tracks to [`assets/music`](../../../assets/music) following its README. No code change is needed.
- **Another TTS engine:** see [`tts/README.md`](tts/README.md).

Keep argument building in pure functions (`*_args`) so it can be unit-tested without running ffmpeg.
