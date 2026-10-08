# `ui/src/pages`

**Overview.** One component per screen of the studio.

## What's here

| File | Screen |
| --- | --- |
| [`Brief.tsx`](Brief.tsx) | New video: the brief form for all three levels, visual sources, uploads, screenshot test and login, YAML import and export |
| [`Run.tsx`](Run.tsx) | One run: script review (medium and high), scene direction with a live Revideo preview and image approval (high), the live production graph and agent cards, quality gates, the final video and downloads, resume and cancel |
| [`Runs.tsx`](Runs.tsx) | Run history |
| [`Settings.tsx`](Settings.tsx) | Providers, models and non-secret settings |

## Extending: a new screen

1. Add `pages/<Name>.tsx` exporting `<Name>Page`. Fetch with `useQuery` and `request()` from `../api/client`; mutate with `useMutation` and invalidate the queries you changed.
2. Add a `<Route>` and a nav link in [`../main.tsx`](../main.tsx).
3. If it needs a new API, add the route on the server first and run `scripts/generate_ui.py` for the types.
4. Add a vitest test for any logic, and keep it usable by keyboard and screen reader (labels, focus order, `aria-live` for progress).
