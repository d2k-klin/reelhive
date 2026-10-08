# `assets/demo`

**Overview.** The demo shown at the top of the README and attached to every GitHub Release, made with ReelHive itself.

## What's here

| File | What it is |
| --- | --- |
| [`brief.yaml`](brief.yaml) | The brief behind the demo (20 s, 16:9, two features) |
| `demo.mp4` | The rendered video with voice and music (attached to releases by `release.yml`) |
| `demo.gif` | A silent 800 px, 12 fps GIF of the same video for the README |

## Regenerating

```bash
uv run reelhive run assets/demo/brief.yaml
cp runs/<run>/video.mp4 assets/demo/demo.mp4
ffmpeg -i assets/demo/demo.mp4 -vf "fps=12,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=64[p];[b][p]paletteuse=dither=none" assets/demo/demo.gif
```

Keep the GIF under about 1 MB so the README loads fast. `tests/unit/test_docs.py` checks that all three files exist, because the README and the release workflow need them.
