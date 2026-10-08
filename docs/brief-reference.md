# Brief reference

A brief is a YAML file. Unknown keys are rejected, so typos fail early with a clear message. Examples are in [examples/briefs](../examples/briefs).

## Every level

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `level` | `small` \| `medium` | `small` | `high` arrives in M3 |
| `audience` | text | required | Who the video is for |
| `storyline` | text | required | The arc in a sentence or two |
| `features` | list, 1-8 | required | One feature beat (and usually one card) each |
| `duration` | seconds, 15-180 | `60` | The end credit counts toward it |
| `format` | `16:9` \| `9:16` \| `1:1` | `16:9` | 1920×1080, 1080×1920, 1080×1080 |
| `voice.gender` | `female` \| `male` | `female` | |
| `closing` | text, ≤60 | required | Must appear verbatim at the end; checked |
| `credit` | `end` \| `corner` | `end` | Hide with `REELHIVE_DISABLE_CREDIT=true` (env only) |
| `visuals` | block | none | See [visuals.md](visuals.md) |

At `small`, accent and speed are fixed to `us` and `1.0`, and production starts straight after the script.

## Medium adds

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `voice.accent` | `us` \| `uk` | `us` | Kokoro voices: `af_heart`, `bf_emma`, `am_michael`, `bm_george` |
| `voice.speed` | 0.8-1.2 | `1.0` | Kokoro speaking speed |
| `tone` | text | `clear and direct` | |
| `pacing` | `slow` \| `balanced` \| `fast` | `balanced` | |
| `brand.colors` | up to 3 `#rrggbb` | none | Accent, background, text |
| `brand.logo` | path | none | Copied into the run folder, shown in a corner |
| `theme` | `default` \| `dark` \| `brand` | `default` | |
| `music_mood` | `calm` \| `upbeat` \| `dramatic` \| `inspiring` \| `tech` | chosen by the music agent | |
| `cta_url` | text, ≤60 | none | Shown on the closing card |

Medium pauses after the script. Edit `runs/<run>/script.json` if you like, then run `reelhive approve runs/<run>`.

## Example

```yaml
level: small
audience: Platform engineers at mid-size SaaS companies
storyline: Cloud bills grow silently. CostHive finds the waste in minutes.
features:
  - Scans every region in one command
  - Flags idle and oversized resources
  - Exports a fix-it report
duration: 60
format: "16:9"
voice:
  gender: female
closing: Try CostHive free on GitHub.
visuals:
  url: http://localhost:3000
```
