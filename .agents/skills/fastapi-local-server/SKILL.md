---
name: fastapi-local-server
description: "Design, secure, implement, or test a local-only FastAPI application, including localhost binding, launch tokens, Host and Origin validation, closed CORS, SSE resume, uploads, downloads, static frontend serving, queues, and graceful cancellation."
---

# Local FastAPI Server

Use this workflow for single-user applications served only on the local machine.

## Procedure

1. Keep routes thin: validate transport data, call an application service, and translate its result to HTTP.
2. Bind only to `127.0.0.1`. Do not expose a host override unless remote access is an explicit product feature with a separate threat model.
3. Generate a high-entropy launch token for each server process and require it on every API request and event stream.
4. Validate `Host` to prevent DNS rebinding and validate `Origin` on state-changing requests. Keep CORS closed by default.
5. Model long-running work in the service layer with persisted state, bounded concurrency, cancellation points, and replayable events.
6. Implement SSE with monotonic event IDs, heartbeat handling, disconnect cleanup, and `Last-Event-ID` resume.
7. Serve built frontend assets from a fixed directory with an SPA fallback that cannot shadow API routes.

## File Safety

- Cap upload sizes and allow-list media types; decode and re-encode untrusted images.
- Generate server-side destination names inside a controlled root.
- Resolve download paths, reject traversal and symlink escapes, and allow-list downloadable artifacts.
- Never accept, return, or persist secrets through settings routes.

## Testing

- Use dependency overrides and a fake service for route tests.
- Test missing/wrong tokens, hostile Host and Origin headers, traversal, oversized uploads, and malformed files.
- Test SSE reconnect from an event ID and disconnect cleanup.
- Assert the server cannot bind beyond loopback.

## Done When

The HTTP layer contains no business logic, the local threat model is enforced by tests, event replay works, and every filesystem operation stays inside an allow-listed root.