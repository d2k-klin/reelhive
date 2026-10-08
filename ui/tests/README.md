# `ui/tests`

**Overview.** Browser tests for the studio. Unit tests for UI logic live next to the code (`src/**/*.test.ts`, run by vitest); this folder holds the end-to-end tests that drive a real browser against the real server.

| Path | What it is |
| --- | --- |
| [`e2e/serve.py`](e2e/serve.py) | Starts the real FastAPI app on 127.0.0.1:8799 with a throwaway workspace and the fixed token `e2e-token` |
| [`e2e/studio.e2e.ts`](e2e/studio.e2e.ts) | Token and Origin rules; every screen in light and dark themes with axe (WCAG 2.1 A/AA); keyboard skip link and focus |

```bash
make test-ui    # builds the UI, then runs Playwright (config: ../playwright.config.ts)
```

## Extending

Name browser tests `*.e2e.ts` (vitest ignores them). For a new screen, add its path and heading to `screens`; it then gets the axe check in both themes automatically. Tests that need a run should create it through the API with the test token, not by writing files.
