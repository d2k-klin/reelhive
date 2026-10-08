# `ui/src/schemas`

**Overview.** Client-side validation of the brief, generated from the same Pydantic model the server uses, so the form rejects exactly what the server would.

## What's here

| File | What it is |
| --- | --- |
| `brief.json` | **Generated**: the `Brief` JSON Schema with every `$ref` expanded |
| `brief.ts` | **Generated**: the zod schema (`briefSchema`) used by React Hook Form |

Regenerate both with `uv run python scripts/generate_ui.py` after changing `src/reelhive/schemas/brief.py`. Don't edit them by hand.
