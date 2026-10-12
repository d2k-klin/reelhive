# Limits

Values below are enforced by the code, so a brief outside them is rejected with a field error.

## Video

| Limit | Value |
| --- | --- |
| Duration | 15 to 180 seconds (default 60). The 3-second intro and the end credit card (1.5 s) count toward the target |
| Duration accuracy | The finished video must land within ±5% of the target (for example 171-189 s for 180 s), or the critic repairs it |
| Narration pace | By `pacing`: `slow` 100-135, `balanced` 130-170, `fast` 145-175 words per minute, not counting the intro, credit, planned holds or the short pause between beats; the floor lowers for a slower voice |
| Shot length | By `pacing`, the average time a screen stays up and the longest any may: `slow` 5.5 s / 8 s, `balanced` 4.5 s / 7 s, `fast` 4 s / 6 s. A scene whose length you set yourself (`duration_override`) is exempt |
| Hold | 0 to 3 seconds of stillness after a scene's voice; the closing scene always settles for 1 second |
| Captions | Phrases of up to 4 words or 28 characters, broken after punctuation; the band takes 16% of the frame's short side |
| Review repair rounds | 2 after the first failed review; then the run stops with the report |
| Scenes | One beat per shot: the time for scenes divided by the pacing's average shot (at least one per key point, plus a hook and a call to action), 2 to 40 beats; at most 40 scenes in a high-level brief |
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

On top of the character limits:

| Check | Limit |
| --- | --- |
| Reading time | At most 4 on-screen words per second a scene is settled (its length minus the 0.8 s entrance) |
| Safe area | Text stays inside a 4% margin on every side of the rendered frame |
| Type size | Rendered text at least 2.2% of the frame's short side (24 px at 1080) |
| Overlap | No text collides with other text, an image or the logo |
| Sharpness | Images enlarged at most 1.35×; the camera caps close-ups at 1.3× |

## Images and capture

| Limit | Value |
| --- | --- |
| Upload formats | PNG, JPEG, WebP; clips as MP4, MOV, M4V, WebM |
| Clips | Up to 200 MB; the first 60 seconds are used, muted. At least 720 px on the short side, either orientation; never enlarged |
| Upload size | 10 MB and 30 megapixels per image (re-encoded on save); requests over 11 MB are refused |
| Minimum scene image size | 1280×720 for `16:9`, 720×1280 for `9:16`, 720×720 for `1:1` |
| Screenshot routes | Up to 10; with none given, up to 10 same-origin pages are discovered |
| Close-up regions | Up to 12 per page; at least 25% of the viewport wide and between 80 px and 1.5 viewports tall |
| Website research | Same origin only, up to 10 pages, the first 3,000 characters of visible text per page |
| Page load | 30 seconds per page; images must finish loading within 10 seconds |
| Sign-in window | 10 minutes to finish signing in |
| Generated images | 0 to 20 per run (default 6); failed attempts count, and product UI is never generated |

## Sound effects

| Limit | Value |
| --- | --- |
| Effects per video | One per started half minute, at most 3 (15-29 s: 1; 30-59 s: 2; 60 s and longer: 3); none is a valid answer |
| Spacing | At least 5 seconds apart |
| Level | -30 to -10 dB; at most -20 dB where it overlaps the voice, -24 dB when its peak lands on a word |
| Placement | Only on moments the renderer reported (a cut, an entrance landing, the camera closing in), with an effect that suits it |

## Publishing

Per-platform video and copy limits are in [publishing.md](publishing.md#limits).

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
