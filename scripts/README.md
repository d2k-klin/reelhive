# `scripts`

**Overview.** Maintenance scripts for the repo. None of them run during a video run.

## What's here

| File | What it does |
| --- | --- |
| [`make_music.py`](make_music.py) | Generates the five placeholder CC0 tracks and `assets/music/manifest.json` with a small numpy synth: `uv run python scripts/make_music.py` |
| [`generate_ui.py`](generate_ui.py) | Regenerates the UI's contracts from Python: `ui/src/api/openapi.json` and `schema.d.ts` (FastAPI routes), `ui/src/schemas/brief.json` and `brief.ts` (the brief validator, via [`generate_zod.mjs`](generate_zod.mjs)): `uv run python scripts/generate_ui.py` |
| [`generate_assets.py`](generate_assets.py) | Design time only: candidate Mr.D poses, role portraits and icons from [`design/prompts`](../design/prompts) via OpenAI image editing with the reference artwork; `--dry-run` prints the prompts |
| [`extract-changelog.sh`](extract-changelog.sh) | Prints one version's section of `CHANGELOG.md`; `release.yml` uses it for release notes: `scripts/extract-changelog.sh v0.1.0` |

## Extending

Add a script when a repo chore is repeated; document it here and wire it into the `Makefile` if people run it often. Scripts must be safe to rerun and must never touch `runs/` or user data.
