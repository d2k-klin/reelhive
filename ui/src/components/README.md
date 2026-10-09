# `ui/src/components`

**Overview.** Small, shared building blocks used across pages.

## What's here

| File | Exports |
| --- | --- |
| [`QuickActions.tsx`](QuickActions.tsx) | M6: the only CopilotKit code. `CopilotKitProvider` with the local AG-UI agent, `SuggestionChips` (`useAgent` + `useFrontendTool('propose_suggestions')`), apply, More ideas, Undo. Lazy-loaded by the Run page. |
| [`suggestions.ts`](suggestions.ts) | The zod schema every `propose_suggestions` call must pass before anything renders |
| [`common.tsx`](common.tsx) | `Field` (a labelled control with an optional hint), `ErrorNote` (an `role="alert"` error), `Status` (a run status pill), `Mascot` (Mr.D art from `@brand` by mood: laptop, walking, working, presenting, inspecting), `VoiceFields` (gender, accent, speed) |

## Extending

Add a component here once two pages need it. Keep components accessible: every control gets a visible label (use `Field`), decorative images get empty alt text, and state is always shown as text as well as colour. New mascot moods come from new art in `assets/brand` (see its README).
