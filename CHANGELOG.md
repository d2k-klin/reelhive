# Changelog

All notable changes to ReelHive are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.1] - 2026-10-13

### Fixed
- Long videos with many short beats overran their target (a 99-second brief drafted at 117 s) and could stop after
  the repair. Kokoro pads every clip with about 0.8 s of silence, which the timing model counted as speech and then
  padded again; with 21 beats that was 17 s. Clips are now trimmed to their speech (`trim_silence()`, word times
  shifted to match), so the voice flows and the draft lands on the target.
- The scene planner and the fixer are held to a reading budget per scene: on-screen words a viewer can read while
  that scene's narration plays (4 words a second, more with a `hold`). It is a validator of their per-run output
  model, so a five-item list on a short beat is fixed before anything is voiced, instead of failing the
  `reading_time` check after the repair and stopping the run. The planner sees each beat's budget in its prompt.
- Dense beats (names, numbers, acronyms) ran past the longest shot: the voice reads them at about 125 wpm, not
  161. The script writer's and fixer's output models now cap words per beat at what one shot holds at that rate
  (12 balanced).
- A plan that still failed its checks after one repair stopped the run, even on a near miss. `recheck` now sends it
  back to `fix` while repairs are left (`MAX_PLAN_REPAIRS`, 3): a bounded cycle like the cut-review loop.

## [0.5.0] - 2026-10-12

### Added
- **Publishing** to YouTube, LinkedIn, TikTok and Instagram Reels, from your machine with your own developer apps
  and accounts (`reelhive connect`, `accounts`, `disconnect`, `publish`, and a Publish panel in the studio). Two
  Strands graphs with a human approval between them: `ready -> publish` drafts the copy per platform (held to each
  platform's limits by a per-run output model), and `ready -> post_<platform>` posts to every chosen platform in
  parallel. `ready` gates credentials, sign-ins and each platform's video rules before any model call or upload; a
  platform that fails doesn't stop the others, one already live is never posted twice, and an interrupted upload is
  never retried silently. Sign-in is OAuth with a loopback redirect, state and PKCE; tokens stay in
  `~/.reelhive/accounts`, owner-only. The subtitles go up as captions on YouTube and LinkedIn, and posts are
  labelled AI-generated where the platform supports it (`publishing.label_ai`). See docs/publishing.md.
- **Sound design.** A `sound` agent between `review` and `master` may add a few quiet effects (whoosh, swish, click,
  pop, chime, low impact; a CC0 library synthesized by `scripts/make_sfx.py`), only on moments the renderer reported
  from its own clock (cuts, entrances landing, the camera closing in) and only with an effect that suits the moment.
  The budget (one per started half minute, at most 3), spacing (5 s) and levels under the voice are validators the
  model must satisfy; none is a valid answer, and often the right one. `sound_effects: false` turns it off.
- **Your own video clips** as scene visuals: MP4, MOV, M4V or WebM in the media folder or uploaded in the studio
  (up to 200 MB). The planner picks a clip by its exact name from its caption, length and size; the resolver
  normalizes it once (H.264, 30 fps, muted, never enlarged, phone rotation applied) and the renderer plays it in the
  device frame, holding the last frame if the scene runs longer.
- **Subtitle files.** Every narrated video gets `video.srt`, `video.vtt` and a selectable subtitle track in the MP4,
  with the same phrases as the burned-in captions (contract-tested against the renderer). Downloads in the studio.
- The layout report now carries each shot's moments (`Moment`: cut, arrive, focus) as well as its geometry.
- **Shorter shots.** The picture now changes about every 4.5 s (balanced; 5.5 s slow, 4 s fast) instead of once per
  key point (about 9-10 s in a 60-second video). The script has one short beat per shot (`beats_for()`: the time for
  scenes over the pacing's average shot), enforced by the script writer's per-run output model, and a new
  `shot_length` hard check fails any screen held longer than the pacing allows (7 s balanced) or a slow average; `fix`
  splits those scenes at sentence boundaries.
- `documents`: PDFs and slide decks as sources. Research reads their text; their pages become scene images the
  planner can pick by name. Upload them in the studio (up to 50 MB each).
- `context`: free-text extra info (facts, pricing, release notes) for every agent and for research.

- Directed video. The scene planner now directs each shot: a `layout` (product centred, or beside its text), a
  `hold` (stillness after the voice so a frame can be read) and a close-up `region` of a screenshot page. Regions are
  measured from the page's DOM at discovery and again at capture, so no pixels go to the planner and the box always
  fits the screenshot.
- `review` node: the rendered cut is checked like a motion designer previews it. Layout gates run on the geometry
  the renderer measured (text inside the safe area, nothing overlapping, type readable on a phone, no blurry
  close-ups); with `frame_review: true`, a vision model also scores one settled frame per shot. A failure loops back
  through `fix -> recheck -> render` (a bounded cycle in the production graph, at most 2 repair rounds).
- `reading_time` hard check: at most four on-screen words per settled second.
- Word-by-word captions (`captions: true`, a toggle in the studio): the narration in short phrases below the content,
  each word lighting up as it is spoken. Timed from Kokoro's own word timestamps, so they also work with the
  narrator off. The caption band is reserved in the layout and checked by the review gates.
- An **AI quick actions** switch on the Script and Scenes screens (the same per-device setting as in Settings).
- A new renderer motion system: elements arrive in reading order on an exact-length spring, one transition grammar
  (the device carried between product shots, a settle into the intro and closing, a push otherwise), device frames
  with depth, a camera that closes in on regions, a drifting backdrop, a counting stat, and the bundled Inter font.

### Changed
- `master` mixes narration, ducked music and sound effects, and writes the subtitles.
- The pause after each beat follows pacing (`TAILS`: 0.6 / 0.5 / 0.35 s, was 0.7 s for all), the word target
  budgets each scene's normal pause, and pace no longer counts the pause between beats as silence.
- Scripts and high-level briefs take up to 40 beats or scenes (was 12).
- `probe()` reports a clip's display size with its rotation applied.
- Studio uploads accept clips; the upload request limit is 201 MB on `/api/uploads` only.
- `httpx` is a direct dependency (the platform APIs).
- The TTS interface returns a `Speech` (length and timed words) instead of seconds.
- `render` is split into `render` (silent cut and layout report), `review` and `master` (audio mix and mux).
- The intro follows an opening hook (a cold open) instead of always playing first (`SceneSpec.intro_at`).
- The closing frame settles for a second and stays on screen under the end credit instead of fading out.
- `pacing` now sets narration density: `slow` 100-135, `balanced` 130-170, `fast` 145-175 words per minute; planned
  holds don't count against the pace.
- The studio's visual source now defaults to `auto`, so the website's screenshots, uploaded images, documents and
  generated images combine out of the box.

### Fixed
- With Copilot, "Let AI describe my images" no longer fails the scenes step: descriptions are skipped and the run
  matches on filenames and captions.
- A blank image folder means no images (it used to resolve to the working directory).
- Research also reads a public App URL when no product website is given (local dev apps are never sent).

## [0.4.0] - 2026-10-09

Notes in, story out: the brief is raw material and the agents do the storytelling.

### Added
- **Research step** (`research`, between brief and script): reads the product website (optional `website` field; same origin, up to 10 pages, masked selectors removed) and writes `research.json` product notes (what it is, correct names, offerings, pains, facts, what each note refers to). The writer, scene planner, critic and fixer build on it. Skipped without a website or when the site can't be read.
- `website` in the brief: researched, and used as the screenshot source unless `visuals` says otherwise.
- Studio: Product website field, **Clear form** button (back to your saved defaults), notes-first labels and help.

### Changed
- **Key points are notes, not copy.** The agents may merge, split and reorder them and write their own wording; beats and scenes record the notes they tell (`covers`), and the gate checks only that every note is told.
- **The closing is an idea.** It is always polished into a finished call to action (typos and names fixed) and no longer checked verbatim; the critic judges it, together with misspelled names, invented facts and broken text. The closing may be up to 200 characters. The eval metric "closing exact match" was removed.
- Prompts for the writer, planner, fixer, critic and suggester were rewritten for storytelling from rough notes.
- **Customization level** (was "control level") is now **Low / Medium / High**: low means the agents own more of the work. `small` is still accepted as `low`. Example briefs are now `low.yaml` and `low-screenshots.yaml`.
- "Run bundle" is now **Download all files (.zip)**, with help explaining what is inside.
- The Frame preview no longer shows your first note as a headline.

### Fixed
- Low-level runs could fail right after the script with `list.remove(x): x not in list` (a race between the draft job and the production job it queues).
- Approving a stopped run replayed the old stop instead of re-checking; approving again now re-runs the quality gates.
- A slow voice could make the duration and pace gates impossible to satisfy together: the pace floor now follows the voice's measured rate, and the fixer gets a word budget at that rate.

## [0.3.0] - 2026-10-09

The studio teaches its own workflow, plus fixes found by the first real productions.

### Added
- **Guided studio:** Mr.D's guide on every page and run state says what is happening, what comes next and when you need to act, based on the real run state.
- **Field and action help:** a keyboard-, mouse- and touch-accessible help button beside unfamiliar settings and actions, explaining consequences, saving, cost, privacy and approvals. It follows its button when the page scrolls.
- **Readable production progress:** the run screen shows stages and quality results in plain language instead of raw events and infrastructure names; diagnostic logs stay downloadable.
- **Illustrated UI guide:** [`docs/ui-guide.md`](docs/ui-guide.md) walks through the studio screen by screen with screenshots; [`docs/ui-tutorial-plan.md`](docs/ui-tutorial-plan.md) records the approach.
- UI tests for the guided flows (field help, brief import and export, sign-in completion, saving scene edits before approval, script approval, run library keyboard access, image approval, settings), with axe at 390 px and 1440 px in both themes.
- The `graphify` project skill for coding agents.

### Changed
- Studio: the brief file actions now share one name, **Import brief file** (top of the page) and **Export brief file**. Export moved to the bottom of the last step, next to the final button, so you export a completed brief.

### Fixed
- Field help tooltips closed as soon as opening them scrolled the page (keyboard focus, taps near the edge, small screens); they now follow their button. This made the tutorial UI tests fail on Linux CI.
- Downloading a live run's `run.log.jsonl` (or another JSON state file) could abort when the run appended to it mid-download; the server now sends a consistent snapshot.
- The image-approval UI test fixture used an invalid brief (`visuals.source: images` without its folder).
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
