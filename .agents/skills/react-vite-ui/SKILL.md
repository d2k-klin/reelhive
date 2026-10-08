---
name: react-vite-ui
description: "Build, structure, debug, or test a React and Vite operational application, including TypeScript, routing, generated API clients, TanStack Query, Zustand event state, forms, accessibility, themes, React Flow, media previews, and Playwright tests."
---

# React + Vite Operational UI

Use this workflow for application interfaces rather than marketing pages.

## Procedure

1. Inspect the repository's React, Vite, TypeScript, and compiler conventions before adding packages or patterns.
2. Organize by user workflow or page. Keep reusable controls in components and transport code in an API layer.
3. Generate API types from the backend schema when available; do not maintain duplicate handwritten contracts.
4. Separate state by ownership:
   - server resources and mutations in TanStack Query;
   - transient live event state in a small external store such as Zustand;
   - form state in the form library;
   - URL-addressable state in the router.
5. Reconcile event-stream updates with query-cache data through one explicit adapter.
6. Build loading, empty, queued, approval, failure, cancelled, reconnecting, and completed states as first-class views.
7. Use accessible primitives, semantic controls, visible focus, keyboard workflows, and reduced-motion support.

## UI Engineering

- Preserve stable layout dimensions for graphs, timelines, media, and live logs.
- Keep dense operational screens scannable; avoid decorative cards and oversized display text.
- Pair status color with text and an icon.
- Virtualize or cap unbounded logs and lists.
- Keep previews and final data on the same validated contract.

## Testing

- Unit test stores and API adapters.
- Component-test conditional fields, validation, event-driven states, and keyboard behavior.
- Run automated accessibility checks in all themes.
- Use Playwright for complete workflows, reconnect behavior, downloads, and responsive layouts.

## Done When

Contracts are generated, state has clear ownership, every long-running state is represented, accessibility tests pass, and the primary workflow works at desktop and mobile sizes.