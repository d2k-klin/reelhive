---
name: playwright-capture
description: "Implement, secure, debug, or test browser automation and screenshot capture with Playwright, including Chromium setup, route crawling, viewports, authentication storage state, selector masking, uploads, and pixel validation. Use for capture pipelines, visual fixtures, or browser-based media generation."
---

# Playwright Capture

Use this workflow for controlled browser capture rather than general end-to-end UI testing.

## Procedure

1. Confirm the pinned Playwright version and installed browser binary. Keep browser installation in project setup or doctor checks.
2. Validate target URLs and allowed schemes. For crawlers, enforce same-origin navigation, a page limit, and a timeout budget.
3. Create a fresh browser context per capture job with an explicit viewport, locale, color scheme, reduced-motion preference, and device scale factor.
4. Define readiness using application signals or a bounded wait. Avoid arbitrary sleeps and unbounded `networkidle` waits.
5. Apply masking before capture and verify required selectors exist when masking sensitive data is mandatory.
6. Save authentication with Playwright storage state after interactive sign-in. Never collect or log passwords, cookies, or tokens.
7. Re-encode and validate captured images before handing them to downstream systems.
8. Close pages, contexts, and browsers on cancellation and every failure path.

## Security

- Treat captured pages as untrusted.
- Block downloads, popups, unexpected origins, and dangerous URL schemes unless explicitly required.
- Store auth state outside committed paths with restrictive permissions.
- Do not send screenshots to external services without an explicit opt-in.

## Testing

- Serve a local fixture site with known routes, login state, and fake secrets.
- Assert crawl limits, viewport dimensions, redirect handling, and mask pixels.
- Test unavailable pages, selector failures, timeouts, and browser cleanup.

## Done When

Capture is bounded, deterministic, privacy-aware, reviewable before downstream use, and covered by a local fixture site requiring no internet access.