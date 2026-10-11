# `renderer/src/components`

**Overview.** The pieces several templates share: the product device and the backdrop.

## What's here

| File | What it is |
| --- | --- |
| [`device.tsx`](device.tsx) | `device()`: a browser window, phone or plain card with a shadow, sized to keep the image's proportions. Its camera holds the full view, then closes in on the scene's focus region (with an accent ring), pans a tall page gently, or pushes in slowly. `MAX_SHARPNESS` caps how far source pixels are enlarged (contract-tested against the review gate). |
| [`captions.tsx`](captions.tsx) | `captionTrack()`: word-by-word captions in the band below the content (on when the spec says `captions`). `phrases()` groups words into short phrases (a break after punctuation, at four words or 28 characters); each word lights up in the accent colour on its own time from the voice. `captionBand()` is the reserved space the layout report measures, so no shot may enter it. |
| [`backdrop.tsx`](backdrop.tsx) | `backdrop()`: the diagonal theme gradient and two soft accent glows that drift for the whole video. |

## Extending

A new device kind belongs in `device.tsx` next to `browser`, `phone` and `none`, with its value added to `VisualAsset.frame` in `src/reelhive/schemas/scene_spec.py` first (then `make schema`).
