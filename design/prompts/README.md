# `design/prompts`

**Overview.** The prompts behind ReelHive's illustrations, one YAML file per kind. `scripts/generate_assets.py` composes each entry with the shared style and turns it into candidates.

## What's here

| File | Contains |
| --- | --- |
| [`_style.yaml`](_style.yaml) | The shared style block (the Mr.D character description), the reference image and the output size |
| [`mascot.yaml`](mascot.yaml) | Six mascot poses: welcome, directing, thinking, celebrating, puzzled, sleeping |
| [`roles.yaml`](roles.yaml) | Mr.D as each of the 12 nodes (brief through render, plus the M6 `suggest` Editor) |
| [`icons.yaml`](icons.yaml) | Illustrated icons (no character, no reference image) with their own `style_override` |

## Format

```yaml
kind: role                      # mascot | role | icon
reference: null                 # optional: overrides _style.yaml's reference (null = text-only)
style_override: "..."           # optional: replaces the shared style
assets:
  - name: role-critic           # unique; becomes design/candidates/<name>/ and the file name
    prompt: Mr.D as a critic holding a magnifying glass and a scorecard.
```

Describe only the pose, prop or object; the character comes from `_style.yaml`. Preview everything with `uv run python scripts/generate_assets.py --dry-run`.
