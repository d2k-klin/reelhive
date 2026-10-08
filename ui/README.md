# ReelHive UI

The local studio is a React/Vite client served by ReelHive's loopback-only FastAPI server.

For end-user instructions and annotated screenshots, see the [UI user guide](../docs/ui-guide.md).

```bash
npm run build --workspace @reelhive/ui
uv run reelhive ui
```

For live frontend work, start the API on port 8765 and run `npm run dev --workspace @reelhive/ui`. The Vite proxy preserves the API Origin check. The launch URL's token is kept in `sessionStorage` and sent with every API call and event stream.

Screens live in `src/pages`, shared controls in `src/components`, generated OpenAPI types in `src/api/schema.d.ts`, and the generated brief validator in `src/schemas/brief.ts`. Run `uv run python scripts/generate_ui.py` after changing Pydantic or FastAPI contracts. Server data belongs in TanStack Query; resumable event state belongs in `stores/events.ts`; form state belongs in React Hook Form.

```bash
npm test --workspace @reelhive/ui                 # vitest: stores and logic
make test-ui                                      # Playwright + axe against the real server (builds first)
```

`tests/e2e/serve.py` starts the real FastAPI app on 127.0.0.1:8799 with a throwaway workspace and a fixed test token; `tests/e2e/studio.e2e.ts` checks the token and Origin rules, every screen in light and dark themes with axe (WCAG 2.1 A/AA), and keyboard navigation. Add a screen, add it to `screens` there.

The Mr.D files under `assets/brand` are supplied brand assets and are excluded from the code license. The UI is fully local and does not load fonts or images from the network.
