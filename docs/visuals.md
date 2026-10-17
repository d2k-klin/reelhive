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

Generated images are never accepted for product UI, including after a fix. PNG, JPEG and WebP are supported. A visual needs at least 720 px on every side, in every format; smaller images fall through to the next source. How large each is really drawn is measured after the render (the review's sharpness check). Screenshots are full-page and use a format-sized viewport (mobile emulation for portrait). `screenshot-pan` pans tall captures inside an optional browser or phone frame.

Before capturing, ReelHive scrolls through the page to trigger deferred images, returns to the top, and waits for fonts and image decoding. Preparation is bounded to 40 scroll steps and 10 seconds; continuous background requests do not prevent capture. Animations are frozen for the shot. HTTP error pages are rejected instead of becoming scene images, and discovery counts the home page only once whether its URL has a trailing slash or not.

The scene planner receives filenames, captions and discovered page titles/headings. It never receives screenshot pixels.

## Your own clips

Put short videos (`.mp4`, `.mov`, `.m4v`, `.webm`) in the same folder as your images, with a caption in `captions.yaml` saying what each one shows: a screen recording of a workflow, the product in use. The scene planner sees each clip's caption, length and size, and picks one by its exact name for a scene it fits (a clip is never matched by guessing). It plays muted in the scene's frame from the shot's start; when the scene outlasts it, the last frame holds, and the planner can give the scene a `hold` so the action finishes.

Each clip is converted once per run (H.264, 30 fps, no sound, never enlarged, phone rotation applied) into `visuals/clips/`. Clips need at least 720 pixels on their short side, in either orientation, and up to 200 MB; the first 60 seconds are used. In the studio, upload clips like images. With `describe_images: true`, one frame from the middle of each clip is described.

```yaml
# captions.yaml
report-in-two-clicks.mov: Creating a cost report in two clicks
```

## Close-ups and layout

Discovery also measures each page's **regions**: sections, forms, tables, figures and large images, each with an id and a label taken from its heading (masked text is left out), up to 12 per page. The planner can point a product scene at one (`visual_request.region: r3`). At capture time the regions are measured again in the same browser session as the screenshot and matched by label, so the box always fits the image even if lazy content moved the page. The scene opens on the page, then the camera glides to the region and outlines it. The camera never enlarges source pixels more than 1.3×, so a close-up stays sharp; a region it can't find is skipped with a note in the progress log.

Product scenes also take a `layout`: `center` for a full view with the text below, `split-left` / `split-right` for the device beside its explanation (stacked on 9:16). Devices keep the image's proportions: a screenshot keeps the capture viewport's shape and scrolls inside it, any other image keeps its own. Caption files map filenames to descriptions:

```yaml
dashboard.png: Main dashboard showing the savings summary
team.webp: Our team working together
```

Images remain local by default. `describe_images: true` explicitly sends supplied images to the scenes provider for descriptions; select a vision-capable Strands provider for this option. Copilot can't read images, so with Copilot the descriptions are skipped (the run carries on with filenames and captions); set `nodes: {scenes: claude}` (or another vision provider) to use them. A blank image folder means no images.

## Photo stories

To tell a story through your own photos, point `visuals.images` at the folder (or drop them in the studio), set `source: images`, and give the brief a `narrator` and a `voice.name` that suits them. The writer sees the photos in the order they were taken (from their EXIF), with their captions, or with a vision description when you set `describe_images: true` (described once per run, in `visuals/descriptions.json`), so the narration says only what each one shows. The planner gives each moment a `photo` scene: the photo across the whole frame under a slow camera move, dissolving into the next. Phones store portrait photos sideways with a rotation tag; ReelHive applies it, so every photo shows upright. A photo too small to fill the frame fails the sharpness check, and the fixer shows it on a card with `image-full` instead.

## Documents

`documents: [./deck.pptx, ./whitepaper.pdf]` (top level of the brief, up to five) adds PDFs and slide decks. Each page is rendered into the run folder's `documents/` at a size that meets every format's minimum, and joins the catalog with its text as the caption. The scene planner picks a page only by its exact name, for a chart, diagram or product slide; keyword matching never picks a document page, so text-heavy pages don't end up on screen by accident. Pages count as provided images, so `source: auto` or `images` uses them and `none` doesn't. Decks are converted with LibreOffice (`soffice`) when it is installed; without it, export the deck as PDF. In the studio, drop the file on **Documents** under the product website.

## Product photos

When the product website describes its products in schema.org structured data (Shopify, WooCommerce and most store themes do), research reads each product's name, price, rating and reviews, and saves up to six of its photos to the run folder's `visuals/product/`. They join the catalog as provided images captioned `Product photo: <name>`, so `source: auto` or `images` can show them and `none` or `screenshots` doesn't. Photos are fetched only from public http(s) addresses, capped at 10 MB and re-encoded before use. The price and reviews are what the `offer` and `review` templates may show.

## Login and preview

```bash
uv run reelhive login http://localhost:3000 --output auth.json
uv run reelhive capture examples/briefs/low-screenshots.yaml --output runs/capture
```

Sign in in the opened browser, then press Enter in the terminal. ReelHive saves session cookies/storage with owner-only file permissions. The default `auth.json` is gitignored; keep any custom filename out of Git too. Reference it in `visuals.screenshots.storage_state`. Passwords are not collected. `mask` selectors are blacked out in the screenshot. Review captures before rendering. Cross-origin screenshot navigation is rejected; external resources needed by the page can still load.

## Generation

Install `uv sync --extra openai`, set `OPENAI_API_KEY`, and set `image_generation.model` in `config.yaml` (see `config.example.yaml`). This is independent of the LLM provider.

Only concept prompts are sent. Style and brand colors are appended consistently. Cached files are keyed by the final prompt, format size, and model inside the run folder. Attempts, including failures, count toward `max_images`, preventing retries or rechecks from exceeding the limit. API usage is logged; `cost_per_image` is an optional user-supplied USD estimate, and an absent estimate is recorded as null, never zero. Source failures and text fallbacks appear in the progress log.
