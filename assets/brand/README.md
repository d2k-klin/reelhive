# `assets/brand`

**Overview.** The Mr.D brand files ReelHive uses: the mascot illustrations shown in the UI (and, later, in the README hero). They are supplied by Dav from the Mr.D brand archive and committed here, so the app works offline and never loads art from a server. **They are not covered by the code licence** (see [`LICENSE.md`](LICENSE.md)); forks keep the code and replace these files.

## What's here

| File | Used for |
| --- | --- |
| `mr-d-laptop.webp` (+ `@2x`) | Sidebar footer, default mascot |
| `mr-d-art-3.webp` (+ `@2x`) | Walking: first launch |
| `mr-d-art-5.webp` (+ `@2x`) | Working: waiting for approval |
| `mr-d-art-7.webp` (+ `@2x`) | Presenting: a run in progress, the finished video |
| `mr-d-art-9.webp` (+ `@2x`) | Inspecting: failed or stopped runs |
| [`manifest.json`](manifest.json) | Every file with its SHA-256 and its source in the archive |
| [`LICENSE.md`](LICENSE.md) | The brand licence |

The UI imports these through the Vite alias `@brand` (`ui/vite.config.ts`), so there is one copy for everything.

## Rules

- Never edit these files by hand. Updates come from Dav as a new set with a new `manifest.json`.
- `tests/unit/test_contract.py` checks every file against its SHA-256 and keeps the set under 2 MB.
- Originals and masters stay in the private S3 archive, not in this repo.

## Extending

The UI plan (§10) asks for six more poses and a role portrait per node (12 in all). Their prompts are in [`design/prompts`](../../design/prompts), and [`design/README.md`](../../design/README.md) explains how candidates are made. Chosen art goes into the brand archive and comes back here with an updated manifest; then add it to the UI's mascot map (`ui/src/components/common.tsx`).
