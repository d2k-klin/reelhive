# `renderer/src/scenes`

**Overview.** Revideo scenes. ReelHive has exactly one, because the spec (not the code) decides what happens: `from-spec` reads the spec variable and plays every scene in order.

## What's here

| File | What it is |
| --- | --- |
| [`from-spec.tsx`](from-spec.tsx) | Draws the background, the logo (if any) and the corner credit (if chosen), then for each spec scene runs `checkScene()` and its template generator (the image layout whenever the scene resolved a visual), then the end credit. |

## Extending

Keep this file an orchestrator. Visual work belongs in a template; ordering rules (an intro, transitions between scenes) can live here as long as total time still equals the spec's `duration`, because Python mixes the audio to that length.
