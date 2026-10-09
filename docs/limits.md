# Limits

Values below are enforced by the code, so a brief outside them is rejected with a field error.

## Video

| Limit | Value |
| --- | --- |
| Duration | 15 to 180 seconds (default 60). The 3-second intro and the end credit card (1.5 s) count toward the target |
| Duration accuracy | The finished video must land within ±5% of the target (for example 171-189 s for 180 s), or the critic repairs it |
| Narration pace | 130-170 words per minute; the floor lowers for a slower voice |
| Scenes | 2 to 12 beats per script; at most 12 scenes in a high-level brief |
| Key points | 1 to 8 per brief |
| Scene length override | 0.5 to 180 seconds |
| Voice speed | 0.8 to 1.2 |
| Frame rate | 30 fps |
| Formats | `16:9` 1920×1080, `9:16` 1080×1920, `1:1` 1080×1080 |

## Brief text

| Field | Limit |
| --- | --- |
| Audience, story | At least 3 characters |
| Closing idea | 3 to 200 characters |
| Product website | 300 characters, `http(s)` only, no embedded credentials |
| CTA URL | 60 characters |
| Brand colors | Up to 3, as `#rrggbb` |
| Music volume | 0 to 1 (default 0.3) |

## On-screen text

Per template. The agents retry until the text fits, and the renderer checks again.

| Template | Limits |
| --- | --- |
| `hook`, `problem`, `image-full`, `screenshot-pan` | Headline 48, subline 80 characters |
| `feature-card` | Label 4, headline 40, body 110 characters |
| `cta` | Headline 60, subline 60, site address 60 characters |
| Intro screen | Title 40, tagline 80, site address 60 characters; shown for 3 seconds, without narration |
| `bullets` | Headline 48 characters; 1 to 5 items of up to 70 characters |
| `stat` | Headline 20, subline 80 characters |

## Images and capture

| Limit | Value |
| --- | --- |
| Upload formats | PNG, JPEG, WebP |
| Upload size | 10 MB and 30 megapixels per image (re-encoded on save); requests over 11 MB are refused |
| Minimum scene image size | 1280×720 for `16:9`, 720×1280 for `9:16`, 720×720 for `1:1` |
| Screenshot routes | Up to 10; with none given, up to 10 same-origin pages are discovered |
| Website research | Same origin only, up to 10 pages, the first 3,000 characters of visible text per page |
| Page load | 30 seconds per page; images must finish loading within 10 seconds |
| Sign-in window | 10 minutes to finish signing in |
| Generated images | 0 to 20 per run (default 6); failed attempts count, and product UI is never generated |

## Runs and providers

| Limit | Value |
| --- | --- |
| Concurrent productions | One at a time; others queue. Draft runs can run alongside |
| Background workers | 4 operations at once |
| Model output | 8,000 tokens per response (`max_tokens` in `config.yaml`) |
| Copilot | 180 seconds per request |
| Regeneration note | 2,000 characters |
| Imported brief file | 100,000 characters |
| Quick actions | 3 to 4 suggestions per beat or scene |

The UI binds to `127.0.0.1` only. See [docs/brief-reference.md](brief-reference.md) for every field and [docs/templates.md](templates.md) for template details.

## Voices and formats

| | US | UK |
| --- | --- | --- |
| female | `af_heart` (default) | `bf_emma` |
| male | `am_michael` | `bm_george` |

Kokoro runs locally on CPU, Apple Silicon or CUDA, at speeds from 0.8 to 1.2. Formats: `16:9` (1920×1080), `9:16` (1080×1920) and `1:1` (1080×1080). Templates are listed in [docs/templates.md](templates.md).
