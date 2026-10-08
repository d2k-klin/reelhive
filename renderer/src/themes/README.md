# `renderer/src/themes`

**Overview.** Colors and fonts. Templates never hardcode a color; they ask for the current theme, which is the default palette overridden by the spec's `theme` (from the brief's theme, brand colors and logo).

## What's here

| File | What it is |
| --- | --- |
| [`default.ts`](default.ts) | `theme` (background, surface, text, muted, accent, font) and `currentTheme()`, which merges the spec's theme over it. |

The Python side builds the spec's theme in `visuals/resolver.py` (`theme_for`): `dark` darkens the background and surface, and brand colors map to accent, background and text, in that order.

## Extending

A new named theme starts in Python: add the value to `Brief.theme` and set its colors in `theme_for()`. The renderer needs no change unless the theme adds a new kind of value (a second font, say). Then add the key here, add it to `Theme` in `scene_spec.py`, and run `make schema`.
