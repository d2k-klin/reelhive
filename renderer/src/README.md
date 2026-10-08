# `renderer/src`

**Overview.** The Revideo project that draws a ReelHive `spec.json`. Python decides *what* is on screen (validated against the schema); this code decides *how it looks and moves*.

## What's here

| Path | What it is |
| --- | --- |
| [`project.ts`](project.ts) | `makeProject` with the single `from-spec` scene. |
| [`spec.ts`](spec.ts) | TypeScript types for the spec, `limitsFor(template)` (reads `maxLength` from the schema) and `checkScene()` (the last guard against overflowing text). |
| [`spec.schema.json`](spec.schema.json) | **Generated** from `src/reelhive/schemas/scene_spec.py` by `make schema`. Never edit by hand; a pytest contract test checks it. |
| [`assets.ts`](assets.ts) | `embedAssets()`: inlines run-local images and the logo as data URLs, refusing any path outside the run folder. |
| [`scenes/`](scenes) | The one scene that walks the spec. |
| [`templates/`](templates) | One generator per template, plus the credit. |
| [`themes/`](themes) | The default palette and `currentTheme()`. |

## Extending

Most changes are a new or changed template: see [docs/adding-a-template.md](../../docs/adding-a-template.md). If the spec gains a field, change the Pydantic model first, run `make schema`, then update `spec.ts`'s types.
