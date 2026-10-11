# `renderer/src/scenes`

**Overview.** Revideo scenes. ReelHive has exactly one, because the spec (not the code) decides what happens: `from-spec` reads the spec variable and plays it as one continuous piece.

## What's here

| File | What it is |
| --- | --- |
| [`from-spec.tsx`](from-spec.tsx) | Waits for the bundled font, draws the backdrop, the corner logo and the corner credit (if chosen), then plays every shot in order, with the intro inserted at `intro_at`: the transition from the previous shot, the entrance (exactly `motion.enter`), the layout report, the hold. The closing shot stays for the end credit. |

The transitions are one grammar for the whole video, picked from what meets at each cut: **carry** (product to product: the device travels to its new place while the screen changes), **settle** (into the intro or the closing: the old shot eases forward and away) and **push** (anything else: the old shot drifts out, the new one comes in from the same direction). The outgoing shot clears in the first half of the cut and the incoming entrance starts as it does, so two compositions never sit on top of each other.

## Extending

Keep this file an orchestrator. Visual work belongs in a template or component; timing rules can live here as long as each shot still takes exactly its duration, because Python times the voice to the scene starts and mixes the audio to the spec's `duration`.
