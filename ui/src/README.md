# `ui/src`

**Overview.** The React studio's source: a single-page app (React 19, React Router, TanStack Query, Zustand) that talks only to the local ReelHive API. See [`../README.md`](../README.md) for running it.

## What's here

| Path | What it is |
| --- | --- |
| [`main.tsx`](main.tsx) | App shell: sidebar, theme switch (system, light, dark), health and provider status, routes |
| [`pages/`](pages) | One component per screen |
| [`components/`](components) | Shared controls (fields, status, mascot, voice fields) |
| [`api/`](api) | The typed API client and the OpenAPI types generated from the server |
| [`schemas/`](schemas) | The brief validator generated from the Pydantic model |
| [`stores/`](stores) | The resumable event store behind the live Run screen |
| [`revideo-player-fix.ts`](revideo-player-fix.ts) | Shim: gives Revideo's `<revideo-player>` a `variables` setter, which React 19 needs to update the preview |
| `style.css`, `a11y.css` | Styles, theming and accessibility helpers |

## Where state lives

Server data lives in TanStack Query, the live event stream in `stores/events.ts`, and form state in React Hook Form validated by the generated zod schema. Don't copy server data into component state except for unsaved edits (as the Run page does for the script and spec).
