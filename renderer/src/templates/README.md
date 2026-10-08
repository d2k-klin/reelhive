# `renderer/src/templates`

**Overview.** One generator function per template. Each takes the view and one scene from the spec and must take exactly `scene.duration` seconds, so picture and pre-mixed audio stay in sync.

## What's here

| File | Template |
| --- | --- |
| [`common.ts`](common.ts) | `playFor(view, node, duration)`: fade and slide in, hold, fade out, remove; always exactly `duration`. |
| [`hook.tsx`](hook.tsx) | `hook`: accent bar, big headline, optional subline |
| [`feature-card.tsx`](feature-card.tsx) | `feature-card`: label number, headline, body |
| [`cta.tsx`](cta.tsx) | `cta`: closing headline and an accent pill (URL) |
| [`image-full.tsx`](image-full.tsx) | `image-full` and `screenshot-pan`: an image or screenshot in an optional browser or phone frame; screenshots pan top to bottom |
| [`extras.tsx`](extras.tsx) | `problem` (a muted hook), `stat` (one big number with a line), `bullets` (a headline and up to five points) |
| [`credit.tsx`](credit.tsx) | `CREDIT_TEXT` (the only copy of the credit text, contract-tested), the end card and the corner badge |
| [`index.ts`](index.ts) | `TEMPLATES`: template name → generator. vitest checks that it covers every template in the schema. |

## Extending

Follow [docs/adding-a-template.md](../../../docs/adding-a-template.md). In short: size from `view.width()` / `view.height()` (all three formats must work), take colors from `currentTheme()`, end with `yield* playFor(...)`, register in `index.ts`, then render it at 16:9, 9:16 and 1:1 and look at it.
