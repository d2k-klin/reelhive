# `renderer/src`

**Overview.** The Revideo project that draws a ReelHive `spec.json`. Python decides *what* is on screen (validated against the schema); this code decides *how it looks and moves*.

## What's here

| Path | What it is |
| --- | --- |
| [`project.ts`](project.ts) | `makeProject` with the single `from-spec` scene. |
| [`spec.ts`](spec.ts) | TypeScript types for the spec, `limitsFor(template)` (reads `maxLength` from the schema) and `checkScene()` (the last guard against overflowing text). |
| [`spec.schema.json`](spec.schema.json) | **Generated** from `src/reelhive/schemas/scene_spec.py` by `make schema`. Never edit by hand; a pytest contract test checks it. |
| [`assets.ts`](assets.ts) | `embedAssets()`: inlines run-local images and the logo as data URLs, refusing any path outside the run folder. |
| [`scenes/`](scenes) | The one scene that walks the spec: shots in playing order, the transition grammar, the layout report. |
| [`templates/`](templates) | One builder per template, plus the intro and the credit. |
| [`components/`](components) | The product device (frames, depth, camera) and the backdrop. |
| [`motion.ts`](motion.ts) | The motion language: the `spring` and `glide` curves, `reveal()` (staggered entrances) and `exactly()`. Durations are always exact. |
| [`stage.ts`](stage.ts) | Frame geometry: the safe content box (moved up to leave a caption band when captions are on), the type scale, `text()`, `stack()` and `hug()`. |
| [`measure.ts`](measure.ts) | The layout report: where each settled shot's elements really are, printed as `REELHIVE_LAYOUT` lines for the `review` node. |
| [`themes/`](themes) | The default palette, the bundled Inter font and `currentTheme()`. |

## Extending

Most changes are a new or changed template: see [docs/adding-a-template.md](../../docs/adding-a-template.md). If the spec gains a field, change the Pydantic model first, run `make schema`, then update `spec.ts`'s types.
