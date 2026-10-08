# `ui/tests/e2e`

**Overview.** Playwright tests that drive Chromium against the real ReelHive server serving the built studio. See [`../README.md`](../README.md) for what they cover and how to add one.

| File | What it is |
| --- | --- |
| [`serve.py`](serve.py) | The test server: real app, throwaway workspace, fixed token, loopback only |
| [`studio.e2e.ts`](studio.e2e.ts) | The studio checks: security, axe in both themes, keyboard |
