# Brief reference

A brief is a YAML file of **notes**, not copy. Write the audience, story, key points and closing idea roughly; the agents research, interpret and write the actual wording (they fix typos and product names too). Unknown keys are rejected, so typos in field names fail early with a clear message. Examples are in [examples/briefs](../examples/briefs).

## Every level

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `level` | `low` \| `medium` \| `high` | `low` | Customization level: low = the agents decide most, high = you direct every scene. `small` is still accepted as `low` |
| `audience` | text | required | Who the video is for |
| `storyline` | text | required | The arc in a sentence or two |
| `features` | list, 1-8 | required | Key points as rough notes. The agents may merge, split or reorder them and write their own wording; the gate only checks that each note is told by some scene |
| `website` | URL | none | Product website: the `research` step reads up to 10 same-origin pages for facts and correct names, and it becomes the screenshot source unless `visuals` says otherwise. Its text goes to your agent provider |
| `duration` | seconds, 15-180 | `60` | The end credit counts toward it |
| `format` | `16:9` \| `9:16` \| `1:1` | `16:9` | 1920×1080, 1080×1920, 1080×1080 |
| `voice.gender` | `female` \| `male` | `female` | |
| `closing` | text, ≤200 | required | The idea of the closing call to action. The agents polish it into a finished line; it is never copied verbatim |
| `credit` | `end` \| `corner` | `end` | Hide with `REELHIVE_DISABLE_CREDIT=true` (env only) |
| `visuals` | block | none | See [visuals.md](visuals.md) |

At `low`, accent and speed are fixed to `us` and `1.0`, and production starts straight after the script.

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

## High adds

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `scenes` | list of 1-12 scenes | planned by the `scenes` agent | Each scene: `index`, `template`, `text` (per template, see [templates.md](templates.md)), `narration`, optional `feature`, `duration_override` (0.5-180 s), `voice_override` (gender, accent, speed), `visual_request` (`kind`, `image`, `route`, `prompt`) |
| `music_track` | file name | chosen by the music agent | A track listed in `assets/music/manifest.json` |
| `music_volume` | 0-1 | `0.3` | Music level under the voice, before ducking |

High pauses twice: after the script (`reelhive approve runs/<run>`), and after the scenes are prepared, so you can review and approve every image (`reelhive approve-scenes runs/<run>`). In between, `reelhive regen runs/<run> --scene 3 --note "..."` redoes one scene and `reelhive preview runs/<run> --scene 3` renders it alone. The UI does the same with buttons. See [examples/briefs/high.yaml](../examples/briefs/high.yaml).

## Example

```yaml
level: low
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
