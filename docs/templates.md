# Templates

Every scene uses one template. Limits are enforced three times: by the agent's structured output (it retries until the text fits), by the critic's hard checks, and by the renderer as a last guard. They come from `src/reelhive/schemas/scene_spec.py`.

| Template | Used for | Fields (max characters) |
| --- | --- | --- |
| `hook` | Opening line, problem statement, any typography-only beat | `headline` (48), `subline` (80, optional) |
| `feature-card` | One feature per card | `label` (4, e.g. `01`), `headline` (40), `body` (110, optional) |
| `problem` | The pain before the product, in muted tones | `headline` (48), `subline` (80) |
| `stat` | One big number with a supporting line | `headline` (20, e.g. `~30% wasted`), `subline` (80) |
| `bullets` | A headline and a short list | `headline` (48), `items` (1-5, each ≤70) |
| `cta` | The closing call to action | `headline` (60, usually the closing message), `subline` (60, e.g. a URL) |
| `image-full` | A provided or generated image with a caption | `headline` (48), `subline` (80) |
| `screenshot-pan` | A full-page screenshot that pans top to bottom inside an optional browser or phone frame | `headline` (48), `subline` (80) |
| `credit` | Not a scene: the "Made with ReelHive by Mr.D" end card (1.5 s) or corner badge | fixed text |

Any scene that resolved a visual is drawn with the image layout, whatever its template, so a `feature-card` with a screenshot shows the screenshot with its headline. A scene whose image could not be resolved falls back to `hook`.

Every template sizes itself from the frame, so the same spec renders at 16:9 (1920×1080), 9:16 (1080×1920) and 1:1 (1080×1080). Colors come from the theme: the default dark theme, `dark`, or `brand`, built from up to three brief colors (accent, background, text) plus an optional logo.

That makes eight templates, plus the credit. To add one, see [adding-a-template.md](adding-a-template.md).
