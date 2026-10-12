# `assets/sfx`

**Overview.** The sound-effect library the `sound` node may score a video with. Six short, quiet effects synthesized by [`scripts/make_sfx.py`](../../scripts/make_sfx.py) from filtered noise and decaying tones with a fixed seed, so every file is reproducible and released as **CC0-1.0**.

## What's here

| Effect | For | Allowed on |
| --- | --- | --- |
| `whoosh-soft.wav` | a shot pushing in from the side | `cut` |
| `swish-short.wav` | the device gliding into its next place | `cut` |
| `click-ui.wav` | the camera landing on a button or control | `focus` |
| `pop-soft.wav` | a number or point landing on screen | `arrive` |
| `chime-bright.wav` | the closing call to action or the logo arriving | `arrive` |
| `impact-low.wav` | settling into the intro or the closing frame | `cut`, `arrive` |

[`manifest.json`](manifest.json) lists each effect's length, its `peak` (the second it is loudest, which the mix lines up with the moment it scores) and the moment kinds it suits. Moments come from the renderer's own clock (`renderer/src/measure.ts`), so a sound can only sit where something visibly happens.

## Extending

Add a generator to `EFFECTS` in `scripts/make_sfx.py` and rerun it: `uv run python scripts/make_sfx.py`. Keep effects short (under two seconds) and quiet, and give each one the moment kinds it suits. A recorded effect is fine too if it is CC0; add it to the manifest by hand with its measured `peak`.
