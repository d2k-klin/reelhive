# `examples/briefs`

**Overview.** Example briefs, one per common use. Copy one and edit it to make your own.

## What's here

| File | Shows |
| --- | --- |
| [`small.yaml`](small.yaml) | The minimum: audience, storyline, features, duration, format, voice, closing. A 60 s, 16:9, typography-only video. |
| [`small-screenshots.yaml`](small-screenshots.yaml) | `small` with `visuals.url`: screenshots of a running app at `http://localhost:3000` |
| [`high.yaml`](high.yaml) | `high`: you write every scene (hook, stat, bullets, feature-card, cta), with a per-scene voice override, a chosen music track and volume; pauses after the script and after the scenes |
| [`medium.yaml`](medium.yaml) | `medium`: 9:16, UK voice, tone and pacing, brand colors and theme, music mood, CTA URL, `visuals.source: auto`; pauses for script approval |

```bash
uv run reelhive run examples/briefs/small.yaml
```

Every field is documented in [docs/brief-reference.md](../../docs/brief-reference.md).

## Extending

Keep examples realistic and fictional, runnable without extra files (or with the setup stated in a comment), and commented where a field isn't obvious.
