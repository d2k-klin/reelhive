ReelHive · by Mr.D

# ReelHive: draft plan

Brief in, video out. An open-source, local-first tool that turns a short brief into a narrated, scored video, using a Strands Graph of agents, Kokoro TTS and Revideo.

draft v0.8UI details: `reelhive-ui-plan.md`Owner: DavDate: 2026-10-08

## Contents

1. [Name](#1-name)
2. [Goals and non-goals](#2-goals-and-non-goals)
3. [Architecture](#3-architecture)
4. [Brief and customization levels](#4-brief-and-customization-levels)
5. [Folder structure](#5-folder-structure)
6. [Tests](#6-tests)
7. [Evals](#7-evals)
8. [README plan](#8-readme-plan)
9. [GitHub repo](#9-github-repo)
10. [Local setup (no Docker)](#10-local-setup-no-docker)
11. [Mr.D brand assets](#11-mrd-brand-assets)
12. [Milestones](#12-milestones)
13. [Risks](#13-risks)
14. [Open decisions](#14-open-decisions)

## 1. Name

**ReelHive** (`reelhive`). It fits the Hive family alongside SentryHive and CostHive, and a graph of cooperating agents is a hive.

Fallback names if needed: Reelwright, BriefReel, StoryHive.

**Distribution:** a public GitHub repo, the same model as SentryHive and CostHive. There is no website, domain or package registry; users install from GitHub.

CLI: `reelhive` · Python package: `reelhive` · Renderer: `renderer/` (a private npm workspace, never published)

## 2. Goals and non-goals

**Goals** - One command: `reelhive run brief.yaml`, producing an MP4 with narration, background music and ducking. - A local web UI (`reelhive ui`) that does everything the CLI does, for people who'd rather not write YAML. Fully specified in **`reelhive-ui-plan.md`**. - Runs locally with no Docker. Only LLM and image-generation calls leave the machine, and Ollama mode with no image generation is fully offline. - Three customization levels: small, medium and high. - Male or female voice, US or UK accent. - Five agent providers: Claude (default), Bedrock, OpenAI, Ollama, and GitHub Copilot through the Copilot SDK. - Three image sources: screenshots of the user's tool, the user's own images, and OpenAI image generation. - A small "Made with ReelHive by Mr.D" credit in every video by default (see 3.7). - A clean Strands Graph that is also a learning reference: parallel branches, conditional edges, and custom non-LLM nodes. - A learning project overall: Strands Graph, the GitHub Copilot SDK and, in a later phase, CopilotKit working together (see 3.10). - Tests, evals and docs good enough for public open source.

**Non-goals (v1)** - No hosted web app or accounts; the UI runs only on the user's machine. - No chat box in the UI. AI quick-action buttons come later (3.10), and conversational editing is only an idea. - No generated music; we ship a curated CC0 library. - No free-form LLM-written Revideo code; agents fill a validated scene spec. - No generated images of the user's product UI (see 3.4). - No hosting of any kind: no SaaS, website, domain, PyPI or npm publishing.

## 3. Architecture

### 3.1 Two graphs

A graph runs to completion, so human approval points sit *between* graph runs.

**Draft graph** (always runs):

```
brief ──► script
```

**Production graph** (runs after script approval, or straight away at `small`):

```
          ┌─► scenes ──► visuals ─┐
script ───┼─► narrate ───────────┼─► timing ─► critic ─┬─(pass)──────────────────► render
          └─► music ─────────────┘                     └─(fail)─► fix ─► recheck ─┬─(pass)─► render
                                                                                  └─(fail)─► stop with report
```

`visuals` depends on `scenes`, because it needs each scene's image request. After `fix`, `recheck` runs the hard checks again, so a broken spec stops with a clear report instead of rendering a bad video.

`render` appears twice in the diagram but is one node with two conditional incoming edges. Strands' join behaviour for conditional edges must be confirmed against the pinned version; if a node waits for all its dependencies, the fallback is two render nodes sharing one executor.

### 3.2 Nodes

| Node | Type | Job |
| --- | --- | --- |
| `brief` | deterministic | Validate input and fill defaults for the chosen level |
| `script` | **agent** (strong model) | Write the narration, already split into beats (one beat per scene) |
| `scenes` | **agent** (fast model) | Map each beat to a template and on-screen text, and write each scene's image request (kind, route, matching image, or generation prompt) |
| `visuals` | deterministic | Resolve each image request: match a provided image, capture a screenshot, or generate one (see 3.4) |
| `narrate` | deterministic | Run Kokoro TTS per beat, producing WAVs and real durations |
| `music` | **agent** (fast) plus a lookup | Choose a mood and BPM, then pick a track from the CC0 library |
| `timing` | deterministic | Set scene lengths from real audio plus padding and transitions |
| `critic` | **agent** (strong) plus hard checks | Pass the spec, or send it to `fix` |
| `fix` | **agent** (strong) | Repair the spec (also the path for broken JSON from weaker models) |
| `recheck` | deterministic | Run the hard checks again on the fixed spec; pass to `render` or stop with a report |
| `render` | deterministic | Call the Revideo renderer, then mix and duck with ffmpeg, producing `video.mp4` |

Deterministic nodes are custom `MultiAgentBase` subclasses, so TTS, screenshots, image calls and rendering never go through an LLM. The image *prompts* are written by the `scenes` agent; `visuals` only executes them.

### 3.3 Hard checks run by `critic` before it calls the LLM

- Total duration within ±5% of the target.
- The closing message is present verbatim in the final scene's narration or on screen.
- Every listed feature is covered by at least one scene.
- Narration pace is 130–170 words per minute.
- On-screen text fits each template's character limits.
- Every image file exists and meets the minimum resolution for the format.
- No `product_ui` scene uses a generated image.

If any check fails, the conditional edge routes to `fix`. If they all pass, the LLM rubric review runs.

### 3.4 Visuals

The `scenes` agent tags every scene with one of three visual kinds:

| Kind | Meaning | Allowed sources, in order |
| --- | --- | --- |
| `product_ui` | Shows the user's actual tool | provided image → screenshot → *downgrade to a text template* |
| `concept` | Illustrates an idea (the problem, a metaphor, the audience) | provided image → generated image → abstract/text template |
| `none` | Typography only (hook, stat, CTA) | none needed |

**Generated images are never used for `product_ui`.** A made-up screenshot of someone's product misleads the viewer and looks wrong next to the real thing. If no real image is available, the scene falls back to a text template instead.

**Source 1: screenshots of the user's tool** (Playwright, headless Chromium) - Input: a URL (local dev server or a live site) and an optional list of routes. With no routes, it crawls up to 10 same-origin pages and the `scenes` agent picks from their titles and headings. - Viewport follows the format: desktop for 16:9 and 1:1, mobile emulation for 9:16. Full-page captures feed the `screenshot-pan` template; a `frame` option wraps them in a browser or phone frame. - Logged-in apps: `reelhive login <url>` opens a visible browser, the user signs in by hand, and the session is saved to a local `auth.json` (Playwright storage state). ReelHive never sees or stores passwords. - `mask` takes CSS selectors (e.g. `.api-key`, `#email`) and blacks them out using Playwright's built-in screenshot masking, so account IDs, emails and keys never reach the video.

**Source 2: the user's own images** - Input: a folder of PNG/JPG/WebP files, plus an optional `captions.yaml` (filename → one-line description). - Matching uses filenames and captions by default, so images stay on the machine. - `describe_images: true` lets a vision-capable model describe each image for better matching. This sends the images to the LLM provider, so it is off by default and the README says so. - At `high`, the user can pin an image to a scene directly.

**Source 3: generated images** (OpenAI image API) - Enabled with `generate:` in the brief and `OPENAI_API_KEY`. It is independent of the LLM provider, so Claude can write the script while OpenAI makes the images. - The `scenes` agent writes one prompt per `concept` scene; `visuals` appends the brief's `style` and brand colors so all images look like one set. - Size is mapped from the format. The model name lives in `config.example.yaml`, never hardcoded. - `max_images` (default 6) caps cost per run. Results are cached by prompt hash in the run folder, so `regen --scene` doesn't pay twice. Cost goes into `run.log.jsonl`. - Generators sit behind `visuals/generators/base.py`, so a Bedrock backend can be added later.

**`auto` mode** (the default) tries the sources in the order in the table above for each scene, using whatever the brief provides. A brief with no URL, no images and no generation still renders, with typography-only templates.

### 3.5 Providers

`providers/factory.py` reads `config.yaml` and returns the executor for each agent node. The graph code never knows which provider is in use.

| Provider | How it runs | Auth | Extra |
| --- | --- | --- | --- |
| Claude (default) | Strands `AnthropicModel` | `ANTHROPIC_API_KEY` | built in |
| Bedrock | Strands `BedrockModel` | AWS profile or IAM | built in |
| OpenAI | Strands `OpenAIModel` | `OPENAI_API_KEY` | `reelhive[openai]` |
| Ollama | Strands `OllamaModel` | none | `reelhive[ollama]` |
| GitHub Copilot | Copilot SDK (`github-copilot-sdk`), wrapped as a custom graph node | Copilot subscription: `copilot` CLI sign-in, or `GH_TOKEN` / `COPILOT_GITHUB_TOKEN`; BYOK also supported by the SDK | `reelhive[copilot]` |

Each provider has two tiers: `strong` (script, critic, fix) and `fast` (scenes, music). The defaults for Claude are `claude-sonnet-5-5` and `claude-haiku-5-5`. Other providers' model names live only in `config.example.yaml`, never hardcoded. Providers can be mixed per node, e.g. `script` on Copilot and `scenes` on Claude.

The `reelhive[openai]` extra covers both the OpenAI LLM provider and image generation.

**How GitHub Copilot fits**

Copilot is not a model that Strands calls. The Copilot SDK runs Copilot's own agent runtime (the same one as Copilot CLI) as a local process and talks to it over JSON-RPC. So Copilot plugs in at the node level instead of the model level:

- **`CopilotAgentNode`** is a `MultiAgentBase` subclass. For each run of an agent node it opens a Copilot session with ReelHive's system prompt for that node, sends the graph input, and returns the result to the graph. The factory puts it in place of the Strands agent; the graph shape and edges stay the same.
- **Structured output:** each node registers one custom tool with the SDK, e.g. `submit_scene_spec`, whose parameters are the Pydantic model. The agent must call it; ReelHive captures the arguments and validates them. Invalid output goes down the same `fix` path as every other provider.
- **Locked down:** Copilot's runtime can run shell commands and edit files. For ReelHive sessions, built-in tools are disabled and the permission handler rejects every request except ReelHive's own submit tool. A test proves that a shell request is refused.
- **Streaming:** sessions run with streaming on, and message deltas become `agent.text` events, so Copilot nodes look the same as any other in the CLI and UI.
- **Models:** whatever the user's Copilot plan offers, listed at runtime by the SDK. `reelhive models --provider copilot` and the UI's model dropdown use that list.
- **Runtime:** the SDK uses a pinned Copilot runtime that it downloads on first use. `make setup` pre-fetches it when the extra is installed, and `reelhive doctor` checks both the runtime and the sign-in. Still no Docker.
- **License:** the Copilot SDK is MIT, compatible with the rest of the stack.

### 3.6 Run folder

Every run is written to disk, which makes runs reproducible and lets you regenerate a single scene:

```
runs/2026-10-08T15-30-00_costhive-launch/
├── brief.yaml        # normalized input
├── script.json       # approved script (beats)
├── spec.json         # final scene spec (the render contract)
├── visuals/          # scene_03_screenshot.png, scene_05_gen_<hash>.png, …
├── audio/            # beat_01.wav … music.wav, mix.wav
├── video.mp4
└── run.log.jsonl     # node timings, tokens, image cost, critic verdicts
```

### 3.7 Credit label

Every video carries a credit: **Made with ReelHive by Mr.D**.

| Mode | What appears | Default |
| --- | --- | --- |
| `end` | A short 1.5s credit after the closing scene, small text at the bottom; it never covers the user's closing message | **yes** |
| `corner` | A small, semi-transparent badge in one corner for the whole video | no |

- The brief picks the placement with `credit: end | corner`; `end` is the default.
- **To turn the visible credit off**, set an environment variable, the same pattern as Revideo's `DISABLE_TELEMETRY`: `bash REELHIVE_DISABLE_CREDIT=true reelhive run brief.yaml` The brief cannot turn it off; only the env var can. `reelhive doctor` and the run log say when the credit is disabled.
- The credit's time counts toward the target duration, so a 60s video stays 60s and the duration check still passes.
- Independently of the mode, ffmpeg always writes an invisible MP4 metadata tag (`comment=Made with ReelHive by Mr.D`), so a video can be traced back to ReelHive even with the visible credit off.
- The text lives in one constant in `renderer/src/templates/credit.tsx`.
- Because the project is open source, anyone can remove the credit in code. Offering an honest off switch keeps goodwill, and most users leave defaults on.

### 3.8 Core service and event stream

**One core, two front ends**

```
CLI (cli.py) ──┐
               ├──► core/service.py ──► draft graph / production graph
UI (server/) ──┘
```

`core/service.py` owns starting runs, approvals, regenerating scenes, cancelling and resuming. The CLI and the UI server are thin layers over it, so features land in both at once.

**Event stream**

`core/events.py` defines one event stream. The CLI prints it as compact progress lines, the UI receives it over server-sent events, and every event is written to `run.log.jsonl` so past runs can be replayed:

| Event | Sent by | Carries |
| --- | --- | --- |
| `node.started` / `node.finished` / `node.skipped` | graph wrapper | node, status, time, tokens, cost |
| `node.task` | every node | one human-readable task line, with progress (e.g. 3 of 8) |
| `agent.text` | agent nodes: Strands callback handler, or Copilot message deltas | streamed text |
| `gate.result` | `critic`, `recheck` | check name, value, threshold, pass/fail |
| `critic.verdict` | `critic` | rubric scores, pass/fail, reasons |
| `fix.diff` | `fix` | before/after of the changed spec fields |
| `run.finished` | `render` | video path, size, duration; or the stop report |

### 3.9 Local UI

`reelhive ui` starts a local web app over the same core: brief form, visuals, script and scene approval, a live Run screen with agents, tasks, quality gates and the video with downloads, run history and settings. Screens, API, security, design, tests and done criteria are all in **`reelhive-ui-plan.md`**.

### 3.10 Later phase: AI quick actions with CopilotKit (learning goal)

**Not part of the first release.** This is milestone M6, after v0.1.0. It's in the plan on purpose as a learning goal: seeing CopilotKit, Strands Graph and the GitHub Copilot SDK working together in one project.

**Two different "Copilots"**

|  | CopilotKit | GitHub Copilot SDK |
| --- | --- | --- |
| What it is | An open-source React framework for in-app AI and generative UI; the makers of the AG-UI protocol | GitHub's SDK for running the Copilot agent runtime |
| Where it sits | The **frontend** of the local UI | The **backend**, as one of the five agent providers (3.5) |
| What ReelHive uses it for | Rendering AI-generated quick-action buttons | Running agent nodes on a Copilot subscription |

They are unrelated libraries and are never mixed up in code or docs.

**The feature**

On the Script screen (per beat) and the Scenes screen (per scene), the user sees 3–4 quick-action buttons written by an agent for that specific beat or scene, e.g. "Punchier hook", "Shorten by \~2s", "Simpler wording", "Stronger call to action". One click regenerates that beat or scene with the suggestion as its note. It is **buttons, not a chat box**.

**How it fits the existing architecture** - **`suggest` agent (new, fast tier):** a Strands agent that receives one beat or scene plus the brief and returns 3–4 suggestions, each with a short label and the instruction text behind it. It is not a graph node; it runs on demand during the approval stops. - **AG-UI endpoint:** the `suggest` agent is exposed through the community Strands ↔ AG-UI integration, mounted inside ReelHive's FastAPI server and protected by the same token, Host and Origin checks as every other route. - **CopilotKit in the UI:** `useCoAgent` shares the selected beat or scene with the agent; the agent's `propose_suggestions` tool is rendered with `useCopilotAction` as the row of buttons. That's CopilotKit's generative UI: the agent's tool call becomes real components. - **Applying a suggestion goes through the existing path:** clicking a button calls the regenerate route that already exists (`/runs/{id}/script/regenerate` or `/runs/{id}/scenes/{n}/regenerate`) with the suggestion's instruction as the note. The agent never edits the spec itself; `core/service.py` still owns every change, and the CLI gets the same suggestions with `reelhive suggest --scene 3`. `core/service.py` keeps the previous version of each beat and scene in the run folder, so every applied suggestion can be undone. - **Events and logs:** `suggestion.offered` and `suggestion.applied` are added to the event stream and `run.log.jsonl`, so you can see which suggestions get used. - **Providers:** in the first version, `suggest` runs on the Strands-based providers (Claude, Bedrock, OpenAI, Ollama). Running it on the Copilot SDK too is a follow-up, and a good test of how the two "Copilots" sit side by side. - **Cost:** suggestions are generated only for the beat or scene in view, cached per version of that beat or scene, and counted in the run's cost.

**Dependency note:** CopilotKit and the AG-UI integration are a sizable addition on top of the existing stack. That's accepted here because learning them is the point, and because the phase is after the first release, so it can't delay it.

**Even later:** a conversational "edit by talking" mode (CopilotKit's sidebar, typing "shorten scene 3 and make the hook punchier") could grow out of the same agent and endpoint. It is only noted, not planned.

Screens, components and tests for this phase are in `reelhive-ui-plan.md`, section 16.

## 4. Brief and customization levels

| Level | You provide | Approval stops | Graph runs |
| --- | --- | --- | --- |
| **small** | audience, storyline, features, duration, format, closing, voice gender; optionally one of `url`, `images` or `generate: true` | none | draft and production back to back |
| **medium** | + tone, pacing, brand colors and logo, music mood, theme, CTA URL, accent, full `visuals` block (routes, masks, style) | script | draft → *approve* → production |
| **high** | + a per-scene spec: template, text, narration, duration, voice, pinned image or prompt per scene; music track and volume | script, scene spec, images | draft → *approve* → production; `reelhive regen --scene 3` |

The graph is the same at every level. Levels only change what `brief` fills from defaults and where the CLI pauses.

**Example: small, with screenshots of a running tool**

```yaml
level: small
audience: Platform engineers at mid-size SaaS companies
storyline: Cloud bills grow silently. CostHive finds the waste in minutes.
features:
  - Scans every region in one command
  - Flags idle and oversized resources
  - Exports a fix-it report
duration: 60          # seconds
format: "16:9"        # 16:9 | 9:16 | 1:1
voice:
  gender: female      # female | male
closing: Try CostHive free on GitHub.
visuals:
  url: http://localhost:3000
credit: end           # end | corner  (disable with REELHIVE_DISABLE_CREDIT=true)
```

**Example: medium visuals block (all three sources)**

```yaml
visuals:
  source: auto                       # auto | screenshots | images | generate | none
  screenshots:
    url: https://app.example.com
    routes: [/dashboard, /scans/new, /reports]
    storage_state: ./auth.json       # from `reelhive login`
    mask: [".account-id", ".user-email"]
    frame: browser                   # browser | phone | none
  images:
    dir: ./my-images
    captions: ./my-images/captions.yaml
    describe_images: false           # true sends images to the LLM provider
  generate:
    provider: openai
    style: clean isometric illustration, soft lighting
    max_images: 4
```

**Voices (Kokoro)**

|  | US | UK |
| --- | --- | --- |
| female | `af_heart` (default) | `bf_emma` |
| male | `am_michael` (default) | `bm_george` |

Plus `speed` (0.8–1.2). TTS sits behind an interface (`audio/tts/base.py`), so Piper can be added later for German.

## 5. Folder structure

```
reelhive/
├── README.md
├── LICENSE                      # Apache-2.0 (matches Strands + Kokoro)
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── CHANGELOG.md
├── Makefile                     # setup, test, eval, lint, demo
├── pyproject.toml               # uv-managed; extras: openai, ollama, copilot, capture, dev
├── uv.lock
├── package.json                 # npm workspaces: renderer, ui
├── config.example.yaml
│
├── src/reelhive/
│   ├── cli.py                   # run, ui, init, doctor, login, capture, preview, regen, voices, models, eval
│   ├── core/
│   │   ├── service.py           # runs, approvals, regen, cancel, resume; shared by CLI and UI
│   │   └── events.py            # event stream for UI + CLI + run log (see 3.8)
│   ├── server/                  # FastAPI for the local UI, plus the M6 AG-UI endpoint (reelhive-ui-plan.md)
│   ├── config.py
│   ├── doctor.py                # checks python, node, ffmpeg, espeak-ng, chromium, keys, Copilot runtime + sign-in
│   ├── levels.py                # defaults + approval stops per level
│   ├── schemas/
│   │   ├── brief.py
│   │   ├── script.py
│   │   └── scene_spec.py        # the render contract (Pydantic → JSON Schema)
│   ├── providers/
│   │   ├── factory.py           # picks the executor per agent node
│   │   └── copilot/
│   │       ├── node.py          # CopilotAgentNode(MultiAgentBase)
│   │       ├── tools.py         # submit_* tools built from the Pydantic schemas
│   │       └── permissions.py   # deny-all handler except ReelHive's own tools
│   ├── agents/
│   │   ├── prompts/             # *.md system prompts, versioned
│   │   ├── script_writer.py
│   │   ├── scene_planner.py     # also writes image requests and prompts
│   │   ├── music_director.py
│   │   ├── critic.py
│   │   ├── fixer.py
│   │   └── suggester.py         # M6: quick-action suggestions (3.10)
│   ├── nodes/
│   │   ├── base.py              # FunctionNode(MultiAgentBase) helper
│   │   ├── brief_node.py
│   │   ├── visuals_node.py
│   │   ├── narrate_node.py
│   │   ├── timing_node.py
│   │   └── render_node.py
│   ├── graphs/
│   │   ├── draft.py
│   │   └── production.py
│   ├── visuals/
│   │   ├── resolver.py          # per-scene source order + fallbacks
│   │   ├── capture.py           # Playwright: routes, crawl, viewport, mask, frame
│   │   ├── login.py             # headed sign-in → storage_state
│   │   ├── provided.py          # folder scan, captions, optional vision describe
│   │   └── generators/{base.py, openai.py}
│   ├── audio/
│   │   ├── tts/{base.py, kokoro.py}
│   │   ├── music_library.py
│   │   └── mixer.py             # ffmpeg sidechain ducking
│   └── render/
│       └── bridge.py            # subprocess → renderer, progress parsing
│
├── renderer/                    # Node / Revideo
│   ├── README.md
│   ├── package.json
│   ├── render.ts                # reads spec.json → renderVideo()
│   ├── src/
│   │   ├── project.ts
│   │   ├── scenes/from-spec.tsx
│   │   ├── templates/           # hook, problem, feature-card, stat,
│   │   │                        # screenshot-pan, image-full, bullets, cta, credit
│   │   ├── frames/              # browser, phone
│   │   └── themes/              # default, dark, brand (from brief colors)
│   └── tests/                   # vitest: spec → scene props
│
├── ui/                          # React + Vite local UI (full layout in reelhive-ui-plan.md)
│
├── design/                      # prompts + style guide for ReelHive's illustrated icons (reelhive-ui-plan.md §10)
├── scripts/generate_assets.py   # prompts + reference image → candidate icons
├── assets/brand/                # Mr.D mascot, role portraits, logos; provided by Dav, committed (section 11)
│
├── assets/music/
│   ├── *.mp3
│   └── manifest.json            # mood, bpm, duration, source, license per track
│
├── examples/briefs/             # small.yaml, small-screenshots.yaml, medium.yaml, high.yaml
│
├── tests/
│   ├── conftest.py              # FakeModel, FakeCopilotSession, FakeImageGenerator, temp run dirs, fixture site server
│   ├── unit/                    # schemas, levels, timing, factory, mixer args, resolver matrix
│   ├── integration/             # graphs end to end with fakes + stub TTS + fixture site
│   ├── e2e/                     # real Kokoro, real Playwright, 3s render (marked slow)
│   └── fixtures/
│       ├── site/                # small static app with login page + fake secrets to mask
│       └── images/
│
├── evals/
│   ├── README.md
│   ├── datasets/briefs/         # 20–30 varied briefs (audiences, lengths, formats, visual sources)
│   ├── metrics/
│   │   ├── deterministic.py     # the critic's hard checks, as scores
│   │   └── judge.py             # LLM-as-judge with rubric
│   ├── rubrics/{script.md, image-prompts.md}
│   ├── run.py                   # reelhive eval --provider claude --set core
│   └── reports/                 # gitignored; HTML/MD comparison reports
│
└── docs/
    ├── architecture.md
    ├── strands-graph.md         # learning notes: graph, conditional edges, custom nodes
    ├── copilot-sdk.md           # learning notes: Copilot as a provider, sessions, tools, permissions
    ├── copilotkit.md            # M6 learning notes: AG-UI, generative UI, how the quick actions work
    ├── brief-reference.md
    ├── visuals.md               # sources, fallbacks, login, masking, privacy
    ├── providers.md
    ├── templates.md
    └── adding-a-template.md
```

## 6. Tests

| Layer | Tool | What it covers | Runs |
| --- | --- | --- | --- |
| Unit | pytest | Schema validation, level defaults, timing math, provider factory, ffmpeg arg building, music selection, the full visual resolver fallback matrix | every push |
| Graph integration | pytest + fakes | Both graphs run end to end with `FakeModel` and `FakeImageGenerator`; the conditional edge takes the fix path when hard checks fail | every push |
| Capture | pytest + Playwright | Screenshots of the local fixture site: routes, crawl limit, viewports, saved login state; masked selectors are verified as solid pixels | every push |
| Renderer | vitest | spec.json → template props; character-limit enforcement; frames | every push |
| Contract | pytest | Pydantic JSON Schema export matches what the renderer validates against | every push |
| Copilot | pytest + `FakeCopilotSession` | `CopilotAgentNode` returns validated output via the submit tool; invalid output takes the `fix` path; shell and file-write requests are refused; message deltas become `agent.text` events | every push |
| Suggestions (M6) | pytest | `suggest` returns 3–4 valid suggestions; applying one calls the existing regenerate path; the AG-UI endpoint enforces the token, Host and Origin checks | every push |
| Events | pytest | Every node emits started/task/finished; skipped nodes emit `node.skipped`; gates emit one `gate.result` per check; the log replays to the same state | every push |
| UI | pytest, vitest, axe, Playwright | API, security, components, accessibility and end-to-end; full list in `reelhive-ui-plan.md`, section 14 | every push |
| Credit | pytest + vitest | Credit present by default in the spec; `end` never overlaps the closing scene; `REELHIVE_DISABLE_CREDIT=true` removes it and the brief alone cannot; metadata tag always written | every push |
| E2E | pytest `-m slow` | Real Kokoro, real Playwright, one-scene 3-second render; checks MP4 duration, audio stream, resolution and the credit metadata tag with ffprobe | nightly + pre-release |

`FakeModel`, `FakeCopilotSession` and `FakeImageGenerator` implement the real interfaces with canned output, so CI needs no API keys. The fixture site is served locally by the test suite, so capture tests never touch the internet.

Targets: 85% line coverage on `src/reelhive` (excluding `cli.py`), and zero external network calls in non-slow tests.

## 7. Evals

Tests check that the code works. Evals check that the *videos are good* and let you compare providers.

**Dataset:** 20–30 briefs in `evals/datasets/briefs/`, covering technical and non-technical audiences, 15s to 3m, all three formats, 1 to 8 features, tricky closings such as URLs and numbers, and every visual source combination (none, screenshots, images, generate, mixed).

**Deterministic metrics** (no LLM): - Schema valid on first try (%), and number of `fix` iterations - Duration error (% vs target) - Closing message exact match - Feature coverage (%) - Words per minute in range - Text-overflow violations - Visual coverage: share of scenes with an image when a source was available - Product UI integrity: generated images in `product_ui` scenes (must be 0) - Tokens, image count, cost, wall time per node

**Judge metrics** (LLM-as-judge with fixed rubrics, scored 1–5): - Script: hook strength, clarity, audience fit, storyline adherence, quality of the call to action - Image prompts: relevance to the beat, consistency with the style, nothing that implies product UI - Suggestions (M6): each one is specific to its beat or scene, and applying it does what the label says (e.g. "Shorten by \~2s" really shortens it)

**Output:** `reelhive eval --providers claude,bedrock,openai,ollama,copilot` writes one comparison report with a table per metric per provider. Prompt changes must not regress the core set by more than 5%. This is the gate before merging any prompt edit.

Evals score the script, spec and image prompts; they never render video or generate images, so a full run is fast and cheap.

## 8. README plan

**Root README.md** 1. Hero: name, one-line pitch, the Mr.D mascot from `assets/brand/` (as in the CostHive and SentryHive READMEs), and a 20s demo GIF made *with ReelHive* 2. Quickstart (under 5 commands): install → `doctor` → `reelhive ui`, or `run examples/briefs/small.yaml` for the CLI, with a UI screenshot 3. How it works: the graph diagram and a short node table 4. Customization levels, with all example briefs linked 5. Visuals: the three sources, the fallback order, `reelhive login`, masking 6. Voices and formats 7. Providers, with config snippets 8. Privacy: what leaves your machine and what doesn't (table below) 9. Contributing, license, credits (Strands, Kokoro, Revideo, Playwright, Copilot SDK, CopilotKit from M6, music sources)

**Privacy table for the README**

| Data | Leaves your machine? |
| --- | --- |
| Brief text, script | Yes, to your agent provider (Claude, Bedrock, OpenAI or GitHub Copilot); no, with Ollama |
| Screenshots | No |
| Your images | No, unless `describe_images: true` |
| Image prompts | Yes, to OpenAI, only when `generate` is on |
| Audio, video, login state | No |

**Sub-READMEs:** `renderer/README.md` (templates, adding one), `ui/README.md` (running the UI in dev mode, adding a screen), `evals/README.md` (running and reading reports), `assets/music/README.md` (licensing rules for added tracks).

## 9. GitHub repo

- **Visibility:** public, Apache-2.0.
- **CI (`ci.yml`):** ruff, mypy, pytest (unit, integration, capture, UI API and security), vitest (renderer and UI), Playwright UI end-to-end, schema contract test, on push and PRs.
- **Nightly (`nightly.yml`):** E2E slow tests and a Claude eval smoke run on 5 briefs, using a repo secret.
- **Release (`release.yml`):** on a `v*` tag, create a GitHub Release with generated notes, the wheel and the demo MP4 attached. Nothing is published to PyPI or npm.
- **Repo hygiene:** issue templates (bug, feature, new template request), PR template with checklist, Dependabot (pip, npm, actions), CODEOWNERS, branch protection on `main`, conventional commits.
- **Discoverability:** topics `strands-agents`, `kokoro-tts`, `revideo`, `playwright`, `copilot-sdk`, `ai-video`, `text-to-video`, `local-first`; a social preview image.

## 10. Local setup (no Docker)

Requirements: Python 3.11–3.12 (pinned to what Kokoro supports), Node 20+, ffmpeg, espeak-ng.

```bash
git clone https://github.com/<owner>/reelhive && cd reelhive   # same owner as SentryHive/CostHive
make setup          # uv sync, playwright install chromium, npm ci + build ui/,
                    # and the Copilot runtime if the copilot extra is installed
reelhive doctor     # checks every dependency and API key
reelhive ui         # opens the local UI in your browser
# or, without the UI:
reelhive run examples/briefs/small.yaml
```

Cloning is the install method, because the Node renderer has to sit next to the Python package. A `uv tool install git+…` or `pip install` route would ship the Python side without the renderer, so it isn't offered.

Kokoro runs on CPU and uses Apple Silicon or CUDA when available. `DISABLE_TELEMETRY=true` is set for every Revideo call.

## 11. Mr.D brand assets

**Rule: every project ships its own copy of the Mr.D files. No project loads images from S3 or any other server.** S3 is the archive where the originals are kept; the files that a project uses are committed into that project's repo.

**Where the files live**

| Place | What it holds | Who uses it |
| --- | --- | --- |
| S3 bucket (private) | The master archive: every pose and role at full resolution, all versions | Dav, as the source to hand out files from |
| Each repo's `assets/brand/` | The Mr.D files that project needs, provided by Dav and committed | That project's README, UI and docs, by relative path |

**S3 archive** - A dedicated private bucket, Block Public Access on, default encryption, versioning on so nothing is ever lost. - No CloudFront and no public URLs; it's never read by a project at build or run time. - Folder layout mirrors the release, e.g. `v1/mascot/`, `v1/roles/`, `v1/logos/`, with the 1024px masters next to the exported WebPs.

**In ReelHive**

```
assets/brand/                 # provided by Dav, committed, never edited by hand
├── LICENSE-brand.md
├── manifest.json             # file list with sizes and SHA-256, provided with the files
├── mascot/                   # sticker, walking, welcome, directing, thinking,
│                             # celebrating, puzzled, sleeping (WebP 1x + 2x)
├── roles/                    # Mr.D as the 11 node roles (WebP 1x + 2x)
└── logos/                    # Mr.D, ReelHive
```

- The README shows the mascot with a relative link (`assets/brand/mascot/sticker.webp`), so it works on GitHub and in any clone.
- The UI imports the same files through a Vite alias, so there is one copy, not two.
- Everything works offline and sends no request anywhere when the app opens.
- **CI check:** every file the code or README references exists, and every file matches the SHA-256 in `manifest.json`.

**Updating the art:** Dav exports a new set from the archive, replaces the files in `assets/brand/` with the new `manifest.json`, and commits. The same applies to every other project that uses Mr.D.

## 12. Milestones

| # | Deliverable | Done when |
| --- | --- | --- |
| **M1** ✅ **Done** (2026-10-08) | End-to-end `small` level | `run small.yaml` produces a 60s 16:9 MP4 with narration and ducked music; CI green; 3 templates |
| **M2** ✅ **Done** (2026-10-08) | `medium` level, all providers, all visual sources | Script approval stop, brand theme, 9:16 and 1:1, all 5 providers including Copilot; screenshots with login and masking, provided images, OpenAI generation, `auto` fallbacks |
| **M3** | `high` level + local UI | Per-scene spec editing, image approval, `regen --scene`; `reelhive ui` meets the "done when" list in `reelhive-ui-plan.md`; 8 templates |
| **M4** ✅ **Implemented** (2026-10-08) | Evals | Eval harness and first cross-provider report; prompt-change gate in CI |
| **M5** | Public v0.1.0 | READMEs and docs complete, demo GIF, GitHub Release v0.1.0, repo public |
| **M6** | AI quick actions with CopilotKit *(later phase, learning goal)* | `suggest` agent behind an AG-UI endpoint; CopilotKit renders 3–4 suggestion buttons per beat and scene; one click regenerates via the existing path; `reelhive suggest` in the CLI; `docs/copilotkit.md` written; released as v0.2.0 |

**M1 notes**
- Templates: `hook`, `feature-card`, `cta`, plus the `credit` card. Provider: Claude only. Brief: `small` level, 16:9 only; other levels, formats and the `visuals` block are rejected with a clear message until M2/M3.
- Confirmed on Strands 1.59 (§3.1): a node runs when *any* incoming edge is satisfied. So `render` is one node with two conditional edges, and the fan-in to `timing` uses a condition that waits for `scenes`, `narrate` and `music`. `visuals` is not in the M1 graph; it arrives with the visual sources in M2.
- `recheck` also re-voices any scene whose narration `fix` changed, then re-times it, so the hard checks never run against stale audio.
- Music: five placeholder tracks generated by `scripts/make_music.py` (CC0, our own) until open decision 3 picks the curated set.
- Revideo 0.11 forces `--single-process`, which full Chrome rejects on macOS, so the renderer uses `chrome-headless-shell`. ffmpeg and espeak-ng fall back to the binaries bundled with `imageio-ffmpeg` and `espeakng-loader` when the system has none.
- Kokoro speaks at about 160 wpm, so the script targets 145 wpm of video time; the rest is padding between scenes.
- Verified locally: every CI step (ruff, mypy, pytest at 94% coverage, vitest, tsc), the slow e2e test, and a full 60s run of `small.yaml` with real Kokoro and Revideo (61.4s, 1920x1080, ducked music, credit and metadata tag), with the LLM answers canned. Still to confirm: the first run with a real `ANTHROPIC_API_KEY`, and the first CI run on GitHub after the push.

**M2 notes**
- Medium runs persist `script.json` and pause before production. Edit the file, then `reelhive approve <run-folder>`; the approved script and config are retained, and approval does not repeat drafting.
- Added 9:16 and 1:1 rendering, brand colors/logo, voice accents/speed, tone/pacing, music mood and CTA URL. `image-full` and `screenshot-pan` bring the template count to five (plus credit); the remaining three templates stay in M3.
- Claude, Bedrock, OpenAI, Ollama and the pinned GitHub Copilot SDK are wired through provider selection, including per-node overrides. Copilot exposes only its validated submit tool, denies other permissions, streams events and cleans up sessions on failure/cancellation.
- Visuals resolve provided images, same-origin masked screenshots with saved login state, and OpenAI concept generation. Product UI cannot use generated images. Generation uses a per-run prompt/model/size cache and an attempt cap. Actual API usage is logged; USD cost is an optional configured estimate, otherwise null.
- Image descriptions are opt-in and currently require a vision-capable Strands scenes provider; Copilot users can override `nodes.scenes`. Screenshots remain local. Minimum source sizes and setup are in `docs/visuals.md`; provider configuration is in `docs/providers.md`.
- Verified locally with fake-provider integration tests, real Chromium capture/masking/login-state tests, renderer tests, Python/TypeScript checks, and real portrait/square renders plus the narrated landscape smoke test. Live paid provider calls and the first GitHub CI run remain unverified.
- Review pass: re-ran every CI step on the M2 commit (ruff, mypy, pytest with all extras at 92% coverage, vitest, tsc) plus the three slow tests. Fixed: the Copilot error message named the wrapper instead of the node; `make test` failed unless the optional provider extras were installed (it now syncs them); a second `reelhive approve` on the same run now gets a clear "already being produced" error and leaves the other process's lock alone.

**M4 notes**
- M3 was skipped here and is being built separately; M4 builds on the M2 commit and does not depend on it.
- `reelhive eval --providers a,b --set core|smoke [--judge P|none] [--baseline F] [--save-baseline F]` runs the real draft and production graphs in spec-only mode: a TTS stand-in sized to Kokoro's measured 161 wpm, no render (the run stops at `spec.json`), placeholder images with the prompts recorded, and screenshots from a fixture site served on 127.0.0.1. Medium briefs are approved as drafted.
- Dataset: 24 briefs (`evals/datasets/briefs`), covering technical and non-technical audiences, 15s to 3m, all three formats, 1 to 8 features, URL and number closings, small and medium levels, and every visual source combination. `smoke` is 5 of them.
- Metrics: the deterministic set from §7 (`evals/metrics/deterministic.py`, built on the critic's hard checks) plus judge scores from fixed rubrics (`evals/rubrics`). Each run writes `report.md`, `report.html` and `results.json`, with one row per metric and one column per provider, plus seconds and tokens per node. Token cost in USD is not computed (no price table); image cost uses `image_generation.cost_per_image` when set.
- Gate: every higher-is-better metric may drop by at most 5% (relative) against `evals/baselines/claude-core.json`; generated product UI must stay at 0. `eval-gate.yml` runs it on PRs that touch prompts, rubrics, the dataset or the baseline, and fails, rather than skipping, without the `ANTHROPIC_API_KEY` secret. `nightly.yml` runs the slow tests and a Claude smoke eval.
- Finding from the first dry run: for 15-20s briefs, a script that hit the word target exactly still overran the duration gate by 6-8%, because the target ignored each scene's minimum padding. `target_words` now caps short videos so the voice plus padding fits; videos of 25s and longer are unchanged. All 24 briefs are now reachable.
- Verified locally with fake providers (unit tests, plus a smoke-set integration run comparing two providers through the real graphs, fixture-site screenshots, the judge, the reports and the gate). Still to do, needing API keys or quota: the first real cross-provider report and the committed Claude baseline (`make eval-baseline`).

`core/service.py` exists from M1, so the UI in M3 is a new front end on finished logic, not a rewrite. M6 adds a feature on top of a released product, so it can't delay v0.1.0.

## 13. Risks

| Risk | Mitigation |
| --- | --- |
| Videos look generic | Put design effort into 8 strong templates and themes before adding more |
| Weak local models break JSON | Pydantic validation plus `fix` repair; evals show the failure rate per provider |
| No German voice in Kokoro | TTS interface from day one; Piper backend planned |
| Music licensing | CC0 only, with source and license per track in `manifest.json` and checked in CI |
| A local server attacked from another browser tab | Localhost bind, launch token, Host and Origin checks, all covered by tests |
| UI and CLI drift apart | Both are thin layers over `core/service.py`; UI API tests compare results with the CLI |
| Copilot's agent runtime can run shell commands and edit files | Built-in tools disabled, deny-all permission handler except ReelHive's submit tools, covered by tests |
| Mr.D art drifts off-model in new poses | Generated from the existing artwork as reference, curated by hand, archived in S3 by version |
| CopilotKit adds a large frontend dependency (M6) | Accepted as a learning goal; isolated to the suggestion components so it can be removed without touching the rest of the UI |
| The Strands ↔ AG-UI integration is community-maintained (M6) | Pin the version, wrap it in one module (`server/agui.py`), and cover it with tests |
| Two runtimes (Python + Node) | One `make setup`, `doctor` command, clear errors from the render bridge |
| Revideo API changes | Pin the version and keep the renderer behind the spec contract |
| Sensitive data in screenshots | `mask` selectors, a `capture` command to review screenshots before rendering, image approval at `high` |
| Generated images look off-brand or misleading | Style and brand colors in every prompt, never used for product UI, image approval at `high` |
| Image generation cost | `max_images` cap, prompt-hash cache, cost logged per run |

## 14. Open decisions

1. GitHub owner: the account or org that holds SentryHive and CostHive.
2. License: **Apache-2.0** recommended (see below); use whatever SentryHive and CostHive use if that is already decided, so the family matches.
3. Source for the initial CC0 music set, 10–15 tracks across 5 moods.
4. Whether `describe_images` should default to on for cloud providers (better matching) or stay off (images never leave the machine). Proposed: off.
5. M6: whether CopilotKit can talk to the AG-UI endpoint in FastAPI directly, or needs its own Node runtime process. If it needs one, `reelhive ui` starts it locally on 127.0.0.1 with the same token checks; still no Docker. To confirm against the pinned CopilotKit version.

**Decided:** CLI, CI and README follow the same conventions as SentryHive and CostHive (command style, flags, output messages, workflow files, README section order, badges). The scaffold copies them from those repos.

**License note:** Apache-2.0 and MIT are both permissive and both compatible with every dependency (Strands, Kokoro and Playwright are Apache-2.0; Revideo, the Copilot SDK and CopilotKit are MIT). Apache-2.0 adds an explicit patent grant and matches Strands and Kokoro. espeak-ng is GPL-3.0, so it stays a system dependency the user installs and is never bundled in the repo.

**Brand assets:** the Mr.D mascot (all poses and roles), the ReelHive logo and the Mr.D name are not covered by the code license. They live in `assets/brand/` (section 11) with their own license file; forks keep the code but replace the brand assets.

ReelHive · open source · local first · UI details in reelhive-ui-plan.md