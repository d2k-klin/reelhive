# `renderer/src/templates`

**Overview.** One builder per template. A builder takes the stage, a layer and one scene from the spec, places its elements and returns a `Shot`. It never decides time: the orchestrator ([`../scenes/from-spec.tsx`](../scenes/from-spec.tsx)) runs the transition, the entrance, the layout report and the hold, so every shot lasts exactly its `duration` and the pre-mixed voice stays in sync.

## What's here

| File | Template |
| --- | --- |
| [`kit.ts`](kit.ts) | The `Shot` and `Builder` contracts, `staggered()` (the default entrance), `shotRoot()` and the accent bar. |
| [`commerce.tsx`](commerce.tsx) | `offer` (the price in the accent colour, an earlier price struck through as it lands) and `review` (a quote under drawn stars, half stars included, or an accent mark) |
| [`statements.tsx`](statements.tsx) | `hook` (accent bar, hero headline, subline), `problem` (the same with a muted mark), `stat` (a big figure that counts up), `bullets` (a headline and a list that hugs its content) |
| [`feature-card.tsx`](feature-card.tsx) | `feature-card`: a raised card with an accent marker, headline and body |
| [`photo.tsx`](photo.tsx) | `photo`: one of the user's photos across the whole frame under a slow camera move for the whole shot (push in, pull out, pan), with an optional caption low in the frame over a soft shade; marked `fullBleed`, so it dissolves in, and it reports its `zoom` for the sharpness gate |
| [`product.tsx`](product.tsx) | `image-full` and `screenshot-pan`: the device with its copy, in the scene's `layout` (`center`, `split-left`, `split-right`; stacked on portrait) |
| [`closing.tsx`](closing.tsx) | `cta`: logo, call to action, accent pill and address; it stays on screen as the last frame. Also `logoMark()`. |
| [`intro.tsx`](intro.tsx) | The intro screen (not a scene): logo or accent bar, the name, tagline and address |
| [`credit.tsx`](credit.tsx) | `CREDIT_TEXT` (the only copy of the credit text, contract-tested), the end card and the corner badge |
| [`index.ts`](index.ts) | `TEMPLATES`: template name → builder. vitest checks that it covers every template in the schema. |

## Extending

Follow [docs/adding-a-template.md](../../../docs/adding-a-template.md). In short: place everything through the stage (`text()`, `stack()`, `hug()`, the type scale), list the elements in reading order as `parts` with their roles so the entrance and the layout report see them, register the builder in `index.ts`, then render it at 16:9, 9:16 and 1:1 and look at it.
