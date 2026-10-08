# renderer

The Node side of ReelHive: [Revideo](https://re.video) scenes that draw a validated `spec.json`. It is a private npm workspace, never published.

```bash
npx tsx render.ts <run>/spec.json <run>/render/silent.mp4   # what render/bridge.py runs
npm test -w renderer                                        # vitest: contract and asset checks
npx -w renderer tsc --noEmit
```

- `render.ts` reads the spec, embeds run-local images as data URLs (paths outside the run folder are refused), and calls `renderVideo` with `DISABLE_TELEMETRY=true`. It prints `progress <0..1>` lines for the Python bridge.
- `src/spec.schema.json` is generated from `src/reelhive/schemas/scene_spec.py` by `make schema`. Don't edit it by hand. `src/spec.ts` reads each template's character limits from it.
- `src/scenes/from-spec.tsx` is the only scene: background, optional logo, every spec scene in order, then the credit.
- `src/templates/` holds one generator per template plus `credit.tsx`, the only place the credit text lives.
- `src/themes/default.ts` is the default palette; the spec's `theme` overrides it.

Revideo 0.11 forces `--single-process`, which full Chrome rejects on macOS, so rendering uses `chrome-headless-shell` (`npx puppeteer browsers install chrome-headless-shell`, done by `make setup`).

Templates and their limits are listed in [docs/templates.md](../docs/templates.md), and [docs/adding-a-template.md](../docs/adding-a-template.md) walks through adding one.
