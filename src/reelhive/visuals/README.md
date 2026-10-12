# `visuals`

**Overview.** Gets an image for every scene that asks for one, from the user's own sources, in a fixed order, and falls back to a text-only scene when nothing suitable exists. Screenshots stay on the machine, and generated images are never used to depict the user's product.

## What's here

| Path | What it is |
| --- | --- |
| [`resolver.py`](resolver.py) | `resolve(ctx)`: for each scene's `visual_request` (`product_ui`, `concept`, `none`), tries a provided image, then a screenshot (product UI) or a generated image (concept), checks resolution, copies files into the run folder, and swaps image templates for `hook` when nothing fits. Also `catalog()` (what the scene planner may choose from), `theme_for()` (brand colors and logo), `image_ok()`, `visual_ok()` (images and clips) and `local_asset()` (path safety). |
| [`provided.py`](provided.py) | The user's media folder: `catalog()` (images and clips plus `captions.yaml`; clips with their length, size and a poster frame), `match()` (images by filename, or by word overlap with the narration), `clip()` (clips only by exact name), and opt-in `describe()` with a vision model (a clip's poster frame stands in for it). |
| [`clips.py`](clips.py) | The user's video clips: `inspect()` (playable, length, display size with rotation applied), `normalize()` (H.264, 30 fps, no audio, never enlarged, cached per source) into `visuals/clips/`, and `poster()`. |
| [`capture.py`](capture.py) | Playwright: `discover()` crawls up to 10 same-origin pages (titles and headings, masked text excluded), and `capture()` takes a full-page, masked screenshot with a format-sized viewport. `same_origin()` and a navigation guard keep saved cookies off other sites. |
| [`login.py`](login.py) | `reelhive login`: opens a visible browser, waits while the user signs in, and saves Playwright storage state with owner-only permissions. Never sees a password. |
| [`generators/`](generators) | Image generation backends (OpenAI today). |

## Source order

| Scene kind | Order |
| --- | --- |
| `product_ui` | planner's clip → provided image → screenshot → text |
| `concept` | planner's clip → provided image → generated image → text |
| `none` | text |

## Extending

- **New source** (e.g. a stock-photo folder or Figma frames): add a module that produces local files, add its step in `resolve()` at the right place in the order, add its settings to `Visuals` in `schemas/brief.py`, and extend the source matrix tests in `tests/unit/test_visuals.py`. Keep the product-UI rule: only real images of the product.
- **New image generator:** see [`generators/README.md`](generators/README.md).

## Rules

Every file a scene uses must live inside the run folder (`local_asset` enforces this), and must meet the minimum resolution for the format (`MINIMUM_SIZE`), or it falls through to the next source.

See also: [docs/visuals.md](../../../docs/visuals.md).
