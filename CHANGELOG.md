# Changelog

All notable changes to ReelHive are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Rendering failed at the very end with `spawn .../ffprobe EACCES` when `node_modules` was installed without install scripts (`npm ci --ignore-scripts` skips the `chmod u+x` of Revideo's bundled ffprobe). The render bridge now restores the execute bit itself, `reelhive doctor` checks it, and the error explains the fix.
- Render progress is logged per percent instead of per frame (a 90 s video wrote about 2,700 events per render attempt into `run.log.jsonl`).

## [0.2.0] - 2026-10-09

M6: AI quick actions with CopilotKit.

### Added
- **Quick actions in the studio:** the selected beat (Script screen) or scene (Scenes screen) gets 3-4 suggested edits as buttons, rendered by CopilotKit from an AG-UI `propose_suggestions` tool call. One click regenerates only that beat or scene; **Undo** restores the previous version; **More ideas** asks for a fresh set; an on/off switch is in Settings.
- `POST /api/agui/suggest` (`server/agui.py`): an AG-UI endpoint over the validated, version-cached `suggest` agent, behind the same token, Host and Origin checks. No CopilotKit runtime process is needed.
- Undo: previous versions are kept in `runs/<run>/versions/`; `POST /api/runs/{id}/script/undo`, `POST /api/runs/{id}/scenes/{n}/undo`, and `reelhive undo <run> --scene N | --script`.
- `reelhive suggest <run> --beat N --apply K` and `--more`; `suggestion.applied` and `version.restored` events.
- An eval metric for quick actions (specific, label fidelity, variety, safe) with `evals/rubrics/suggestions.md`.
- Browser tests for quick actions against the real server with a fake model, including that no request leaves 127.0.0.1; a unit test that malformed tool output is rejected.

### Fixed
- The Scenes screen went blank whenever the live preview changed: React 19 sets custom-element props as properties, and Revideo's `<revideo-player>` has a getter-only `variables`. A small shim adds the setter, and an error boundary now shows a message instead of a blank page.
- Colour contrast of the "Live" indicator (WCAG AA).

### Security
- CopilotKit's `@scarf/scarf` install analytics are disabled (`scarfSettings` in `package.json`).

## [0.1.0] - 2026-10-09

The first public release: milestones M1 to M5, plus the backend of M6.

### Added
- **M1, `small` level end to end:** `reelhive run brief.yaml` turns a brief into a narrated 16:9 MP4 with ducked background music. Two Strands graphs (draft and production) with parallel branches, a conditional `fix` path and custom deterministic nodes; Kokoro TTS; a Revideo renderer driven by a validated scene spec; the "Made with ReelHive by Mr.D" credit (end card or corner badge, `REELHIVE_DISABLE_CREDIT=true` to hide it; the metadata tag is always written); `reelhive doctor`.
- **M2, `medium` level:** script approval stop (`reelhive approve`), 9:16 and 1:1, brand colors and logo, voice accents and speed, tone, pacing, music mood and CTA URL. Providers: Claude, Bedrock, OpenAI, Ollama and GitHub Copilot (through the Copilot SDK, locked down to a single submit tool), with per-node overrides. Visual sources: provided images, masked screenshots with saved login state (`reelhive login`, `reelhive capture`), OpenAI concept generation with a cache and a cap, and `auto` fallbacks; generated images never stand in for product UI. Templates `image-full` and `screenshot-pan`.
- **M3, `high` level and the local studio:** write every scene yourself (template, text, narration, duration, voice, image), with stops after the script and after the scenes, image approval, `reelhive approve-scenes`, `reelhive regen --scene N`, cancel and `reelhive resume` from checkpoints. Templates `problem`, `stat` and `bullets` (eight in all). `reelhive ui`: a React studio served by a FastAPI app bound to 127.0.0.1 with a launch token and Host and Origin checks, covering brief setup, uploads, screenshot tests and login, YAML import and export, script and scene editing with a live Revideo preview, the live graph and gate log, run history, downloads and settings. The UI's API types and brief validator are generated from the Python models.
- **M4, evals:** `reelhive eval` compares providers on a 24-brief dataset in spec-only mode (no video, no paid images), with deterministic metrics, an LLM judge with fixed rubrics, Markdown/HTML/JSON reports and a 5% regression gate (`eval-gate.yml`). Nightly slow tests and a Claude smoke eval.
- **M5, docs and release:** a README in every folder (what it is, what's in it, how to extend it), architecture and learning notes, the brief and template references, community files, issue and PR templates, Dependabot, CODEOWNERS, and a release workflow. The demo video is made with ReelHive.
- `reelhive init`, `reelhive voices` and `reelhive preview --scene N`; `examples/briefs/high.yaml`; the run log now records when the visible credit is disabled.
- `design/`: the Mr.D style guide and prompts for the remaining mascot poses, role portraits and icons, and `scripts/generate_assets.py` to make candidates from the reference artwork.
- **M6 (backend), quick actions:** a `suggest` agent that offers 3-4 specific edits for one beat or scene, cached per version and logged as `suggestion.offered`; `reelhive suggest <run> --beat N | --scene N`. The CopilotKit buttons and one-click apply follow in 0.2.0.

### Removed
- The raw source PNGs of the Mr.D artwork from `assets/brand/` (about 8 MB). Only the WebP files the UI uses ship; originals belong in the brand archive (they remain in Git history).

### Fixed
- Short videos (15-20 s) overran the duration check because the script's word target ignored per-scene padding; found by the first eval dry run.
