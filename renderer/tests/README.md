# `renderer/tests`

**Overview.** vitest tests for the renderer's pure logic. They never start a browser; real renders are covered by the Python e2e tests.

## What's here

| File | Covers |
| --- | --- |
| [`spec.test.ts`](spec.test.ts) | Limits are read from the generated schema; overflowing text and unknown templates are rejected; `TEMPLATES` has a component for every template in the schema |
| [`assets.test.ts`](assets.test.ts) | Images and the logo are embedded as data URLs without changing the saved spec; `..` traversal and symlinks out of the run folder are refused |

```bash
npm test -w renderer
```

## Extending

Test logic that decides something (limits, paths, layout maths) here. If you're tempted to test how a template looks, render it with `make test-slow` and look instead.
