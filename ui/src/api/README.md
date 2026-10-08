# `ui/src/api`

**Overview.** How the UI talks to the local server, with types generated from the server itself so the two can't drift.

## What's here

| File | What it is |
| --- | --- |
| [`client.ts`](client.ts) | `request()` (adds the launch token, JSON in and out, typed errors), `apiUrl()` and `fileUrl()` (token in the query string for `<video>`, downloads and EventSource), and the main types (`Brief`, `Run`, `Script`, `Spec`, `Config`) picked from the generated schema |
| `openapi.json` | **Generated**: the server's OpenAPI document |
| `schema.d.ts` | **Generated**: TypeScript types from `openapi.json` (openapi-typescript) |

The launch token arrives once in the URL (`?token=`), moves to `sessionStorage`, and is removed from the address bar.

## Regenerating

After changing a FastAPI route or a Pydantic model:

```bash
uv run python scripts/generate_ui.py
```

Never edit the generated files by hand.
