# `assets`

**Overview.** Files ReelHive ships with: the music library the `music` agent chooses from, and the demo shown in the README and attached to releases. Every project file is committed, and nothing is loaded from a server at run time.

## What's here

| Path | What it is |
| --- | --- |
| [`music/`](music) | The CC0 music library and its `manifest.json` |
| [`demo/`](demo) | The demo video and GIF, and the brief that made them |

The Mr.D brand files (mascot, role portraits, logos) will live in `assets/brand/` with their own licence and a SHA-256 manifest (plan §11). They are not covered by the code licence.

## Extending

Keep binary files small: cloning is the install method. Every asset needs a clear licence: CC0 for music, ours for the demo, and Dav's brand licence for `brand/`.
