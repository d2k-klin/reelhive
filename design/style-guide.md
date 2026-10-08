# Mr.D style guide

Every illustration in ReelHive looks like it came from the same studio: Mr.D's. Use this guide when writing prompts, choosing candidates, and reviewing a pull request that adds art.

## The character (never changes)

- Glossy 3D vinyl-toy style with a thick **white sticker outline**.
- A black head shaped like the letter **D**, with a **lime glow** along its curved edge.
- Black glasses with lime-lit rims; glowing lime smiling eyes.
- Black hoodie with lime drawstrings, cargo pants with lime trim and a cloud patch, a backpack, black sneakers with glowing lime soles.

## Palette

| Use | Colour |
| --- | --- |
| Body, objects | near-black `#111111` – `#1c1c1c`, glossy |
| Glow, accents | lime `#b4f000` (use sparingly: edges, eyes, soles, small details) |
| Outline | white `#ffffff` sticker outline |
| Background | **transparent**: every asset must read on near-black and on warm ivory `#f6f1e7` |

## Do

- Generate from the existing artwork as a **reference image** (image editing), never from text alone.
- One clear prop per role, with a silhouette that reads at 48 px (cropped to head and prop for avatars).
- Keep lighting soft and frontal, and leave room around the figure for the outline.

## Don't

- Don't change the head shape, glasses, colours or outfit.
- No text in images (the UI always shows the role or label as real text), and no third-party logos.
- No background scenes, gradients or drop shadows that break on a transparent background.
- Don't depict product UIs or screens with readable content.

## Checklist before committing an asset

- [ ] Same character as `mr-d-laptop.webp` side by side (head, glasses, glow, outfit).
- [ ] Transparent background; checked on near-black and ivory.
- [ ] Exported as WebP at 1x and 2x (plus a 1024 px master for the archive).
- [ ] Mascot and role art goes to Dav's brand set and is supplied in `assets/brand/` with `manifest.json`; icons go to `ui/src/assets/icons/`.
- [ ] Disclosed as AI-generated from the Mr.D artwork and curated by hand (README / About).
