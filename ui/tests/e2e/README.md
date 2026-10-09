# `ui/tests/e2e`

**Overview.** Playwright tests that drive Chromium against the real ReelHive server serving the built studio. See [`../README.md`](../README.md) for what they cover and how to add one.

| File | What it is |
| --- | --- |
| [`serve.py`](serve.py) | The test server: real app, throwaway workspace, fixed token, loopback only; `--fake` adds fake models and isolated runs for review, images, failure, and completion |
| [`quick-actions.e2e.ts`](quick-actions.e2e.ts) | M6 quick actions end to end (fake model) |
| [`studio.e2e.ts`](studio.e2e.ts) | The studio checks: security, axe in both themes, keyboard |
| [`tutorial.e2e.ts`](tutorial.e2e.ts) | Help interactions, synchronized duration, compact long briefs, progress layout, draft/import/export, approvals, image reset, settings persistence, mobile and desktop accessibility. |
