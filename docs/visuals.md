# Visuals

`small` and `medium` accept the same visual sources. All paths are relative to the directory where you invoke ReelHive; the normalized brief stores absolute paths so you can approve from another directory.

```yaml
visuals:
  source: auto  # auto | screenshots | images | generate | none
  screenshots:
    url: http://localhost:3000
    routes: [/dashboard, /reports] # omit to discover up to 10 same-origin pages
    storage_state: ./auth.json
    mask: [".account-id", ".user-email"]
    frame: browser  # browser | phone | none
  images:
    dir: ./my-images
    captions: ./my-images/captions.yaml # defaults to captions.yaml in the image folder
    describe_images: false
  generate:
    provider: openai
    style: clean isometric illustration, soft lighting
    max_images: 4
```

Shortcuts: `visuals: {url: http://localhost:3000}`, `visuals: {images: ./my-images}`, or `visuals: {generate: true}`. Generation defaults to a cap of six images. `source` restricts which sources are used; `none` makes the entire video typography-only.

| Scene kind | Auto source order |
| --- | --- |
| Product UI | Matching provided image → screenshot → text |
| Concept | Matching provided image → generated illustration → text |
| None | Text |

Generated images are never accepted for product UI, including after a fix. PNG, JPEG and WebP are supported. Minimum visual resolution is 1280×720 for landscape, 720×1280 for portrait, and 720×720 for square. Images below those sizes fall through to the next source. Screenshots are full-page and use a format-sized viewport (mobile emulation for portrait). `screenshot-pan` pans tall captures inside an optional browser or phone frame.

The scene planner receives filenames, captions and discovered page titles/headings. It never receives screenshot pixels. Caption files map filenames to descriptions:

```yaml
dashboard.png: Main dashboard showing the savings summary
team.webp: Our team working together
```

Images remain local by default. `describe_images: true` explicitly sends supplied images to the scenes provider for descriptions; select a vision-capable Strands provider for this option. With Copilot as default, you can set `nodes: {scenes: claude}` (or another supported vision provider).

## Login and preview

```bash
uv run reelhive login http://localhost:3000 --output auth.json
uv run reelhive capture examples/briefs/low-screenshots.yaml --output runs/capture
```

Sign in in the opened browser, then press Enter in the terminal. ReelHive saves session cookies/storage with owner-only file permissions. The default `auth.json` is gitignored; keep any custom filename out of Git too. Reference it in `visuals.screenshots.storage_state`. Passwords are not collected. `mask` selectors are blacked out in the screenshot. Review captures before rendering. Cross-origin screenshot navigation is rejected; external resources needed by the page can still load.

## Generation

Install `uv sync --extra openai`, set `OPENAI_API_KEY`, and set `image_generation.model` in `config.yaml` (see `config.example.yaml`). This is independent of the LLM provider.

Only concept prompts are sent. Style and brand colors are appended consistently. Cached files are keyed by the final prompt, format size, and model inside the run folder. Attempts, including failures, count toward `max_images`, preventing retries or rechecks from exceeding the limit. API usage is logged; `cost_per_image` is an optional user-supplied USD estimate, and an absent estimate is recorded as null, never zero. Source failures and text fallbacks appear in the progress log.
