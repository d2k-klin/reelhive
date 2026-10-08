# ReelHive UI: Plan

> The local web UI for ReelHive. Everything the CLI does, in a browser, on your own machine.

Status: draft v0.4 · Owner: Dav · Date: 2026-10-08 · Companion to `reelhive-plan.md`

---

## 1. Purpose and principles

- **Same result as the CLI.** The UI and the CLI are thin layers over one core (`core/service.py`). A video made in the UI is identical to one made from a brief file.
- **Local only.** One user, one machine, bound to `127.0.0.1`. No accounts, no hosting.
- **Nothing hidden.** Every agent, task, quality gate and decision is visible while it happens and replayable afterwards.
- **A window into Strands Graph.** The Run screen draws the live graph, so the UI doubles as a way to see how the graph executes.
- **Briefs move freely.** Any brief made in the UI can be exported as YAML for the CLI, and any YAML brief can be imported into the UI.
- **Secrets stay in the environment.** API keys and sign-ins are never typed into the UI.

---

## 2. Launching

```bash
reelhive ui                      # start and open the browser
reelhive ui --port 8765          # fixed port (default: a random free port)
reelhive ui --no-open            # print the URL, don't open a browser
reelhive ui --runs-dir ~/videos  # use another runs folder
```

On start it prints one line like `ReelHive UI: http://127.0.0.1:53114/?token=…` and opens it. The token is stored in the browser session and sent with every API call. Ctrl+C stops the server; a running render is cancelled cleanly at the next node boundary.

---

## 3. Architecture

```
Browser (React app)
   │  REST + server-sent events, token on every call
   ▼
FastAPI server  (src/reelhive/server/)
   │  thin routes, no business logic
   ▼
core/service.py ──► draft graph / production graph
   │
   └─► core/events.py ──► SSE to the browser + run.log.jsonl
```

- **Backend:** FastAPI inside the Python package. Routes only validate input and call `core/service.py`.
- **Live updates:** one server-sent events stream per run. Every event has an ID, so a reconnecting browser resumes with `Last-Event-ID` and misses nothing.
- **Frontend:** React + Vite + TypeScript in `ui/`, built to static files that FastAPI serves. No separate Node server runs at use time.
- **Dev mode:** `make ui-dev` runs the Vite dev server with hot reload, proxying `/api` to FastAPI.
- **Typed API:** the TypeScript client is generated from FastAPI's OpenAPI schema (`openapi-typescript`), so the UI breaks at build time, not at run time, when the API changes.
- **Concurrency:** one production run at a time (TTS, capture and rendering are CPU-heavy). Further runs queue and the Runs screen shows their position. Draft runs (script only) can run alongside.

**Frontend libraries** (all MIT-licensed)

| Need | Library |
|---|---|
| Server state, caching | TanStack Query |
| Live run state from events | Zustand (one small store per open run) |
| Routing | React Router |
| Accessible components | Radix primitives, styled with Tailwind |
| Graph view | React Flow (xyflow) |
| Scene preview | Revideo `<Player/>` |
| Forms and validation | React Hook Form + Zod schemas generated from the Pydantic models |

---

## 4. Security

A local server can still be reached by other websites open in the same browser, so it gets real protection.

- Binds to `127.0.0.1` only, never `0.0.0.0`. There is no flag to change this.
- A random token is generated at every launch and must be sent on every API call and the event stream, the way Jupyter does it.
- The `Host` header must be `localhost` or `127.0.0.1`, which blocks DNS-rebinding attacks.
- `Origin` is checked on every write request, and CORS is closed.
- Uploads accept only PNG, JPG and WebP, are capped in size, are re-encoded on save, and are written only inside the run folder.
- File downloads go through an allow-list of paths inside the run folder; no path from the browser is used directly.
- API keys are never accepted, stored or shown. Settings show only whether each one is set.
- Sign-in to the user's own app happens in a separate visible browser window that Playwright opens; the UI never sees the password.

---

## 5. Layout and navigation

- **Left sidebar:** New video, Runs, Settings.
- **Top bar:** status chips for what's ready, e.g. "Claude ✓", "Copilot: signed in", "Image generation: no key", "ffmpeg ✓". Clicking a chip opens the matching Settings tab.
- **Light and dark themes**, following the system by default.

**The New video flow** is a stepper. The steps shown depend on the level:

| Level | Steps |
|---|---|
| small | Brief → Run |
| medium | Brief → Visuals → Script (approve) → Run |
| high | Brief → Visuals → Script (approve) → Scenes (approve, incl. images) → Run |

At `small`, the Brief step includes a compact visuals box (one URL, an image folder, or "generate images"), so it stays one screen.

---

## 6. Screens

### 6.1 Brief

| Field | Control | Level | Notes |
|---|---|---|---|
| Level | segmented switch: small / medium / high | all | Switching up reveals fields; switching down keeps hidden values but ignores them |
| Audience | text | all | |
| Storyline | multiline text | all | |
| Features | list editor: add, edit, drag to reorder, remove | all | At least one |
| Duration | slider 15–180s + number input | all | Shows an estimated scene count |
| Format | three cards: 16:9, 9:16, 1:1 | all | Small frame preview on each card |
| Voice | gender + accent cards, each with ▶ sample | all | Sample is a short Kokoro clip, generated once and cached |
| Speed | slider 0.8–1.2 | medium+ | Replays the sample at the chosen speed |
| Closing message | text with character count | all | Marked as "must appear exactly" |
| Tone, pacing | dropdowns | medium+ | |
| Brand colors, logo | color inputs, logo upload | medium+ | Live preview of the theme on a sample frame |
| Music mood | cards with ▶ previews from the CC0 library | medium+ | |
| Theme | default / dark / brand | medium+ | |
| CTA URL | text | medium+ | |
| Credit placement | end / corner | all | If `REELHIVE_DISABLE_CREDIT` is set, shows "Credit is off (environment variable)" as read-only text |

- **Validation** runs as you type with Zod schemas generated from the Pydantic models, and again on the server. Server errors are mapped back onto the right field.
- **Import / export:** "Load brief file" imports a YAML brief; "Export brief" downloads the current form as YAML for the CLI.
- **Drafts** are kept in the browser while you type, so a refresh doesn't lose work.

### 6.2 Visuals

A source selector at the top: **auto** (default), screenshots, images, generate, none. Each source has its own panel:

**Screenshots**
- App URL and a route list (chips; add, remove, reorder). An empty list means "crawl up to 10 pages".
- **Sign in to your app:** starts `reelhive login` on your machine, which opens a visible browser window. The UI shows "Waiting for you to finish signing in…" and switches to "Signed in, session saved" when done.
- **Mask selectors:** CSS selector chips (e.g. `.api-key`, `#email`).
- **Frame:** browser / phone / none.
- **Test capture:** captures the routes now and shows thumbnails with masks applied, so you can check that nothing sensitive is visible before any video is made.

**Your images**
- Drag-and-drop upload for many files at once, as a thumbnail grid.
- A one-line caption field under each image (stored as `captions.yaml`).
- "Let the AI describe my images" toggle, off by default, with a plain warning: "This sends your images to your LLM provider."

**Generate images**
- On/off toggle, style text, and max images (default 6).
- A line showing the most images this run can generate.
- If `OPENAI_API_KEY` is missing: the toggle is disabled with "Set OPENAI_API_KEY to enable image generation".
- A fixed note: "Generated images are never used for scenes showing your product."

### 6.3 Script (approval stop at medium and high)

- One card per beat: editable narration, estimated seconds and words per minute (updated live), and chips for the features it covers.
- The closing beat is highlighted; editing it so the closing message no longer matches shows a warning.
- A summary bar: total estimated duration vs target, and feature coverage (e.g. "3 of 3 features").
- Actions: **Approve and continue**, **Regenerate script** (with an optional note such as "make the hook punchier"), **Back**.
- Edits are saved with the approval and recorded in the run log.
- *Later (M6):* AI quick-action buttons under each beat, built with CopilotKit (section 16).

### 6.4 Scenes (approval stop at high)

- A horizontal timeline strip of scene thumbnails, with widths proportional to duration.
- Selecting a scene opens a detail panel:
  - template dropdown, on-screen text with a character limit counter, narration, duration override, voice override
  - visual: kind (product UI / concept / none), source, and the image: pick from your images, choose a route to capture, or edit the generation prompt
  - **Preview:** the Revideo player plays this scene from the spec, instantly, without rendering an MP4
  - **Regenerate this scene**, with an optional note
  - **Approve image** checkbox
  - *Later (M6):* AI quick-action buttons for this scene, built with CopilotKit (section 16)
- **Approve all and render** is enabled only when every scene's image is approved or the scene has no image.

### 6.5 Run

One live screen, in three parts from top to bottom. The Mr.D mascot sits in the header in its "directing" pose while the run is in progress (section 10.1).

**Part 1: agents and tasks**
- The production graph drawn with React Flow, each node shown with its agent's round portrait (section 10.2). Nodes change state live: waiting (grey), running (pulsing), done (green), failed (red), skipped (dashed, e.g. `fix` when the critic passed). Parallel branches visibly run at the same time, and the edge actually taken out of `critic` and `recheck` is highlighted.
- One card per node, in graph order:
  - the agent's portrait, with its state shown as a ring or badge
  - name, role, and type (agent or deterministic)
  - for agents: the provider and model (e.g. "Claude · `claude-sonnet-5-5`" or "Copilot · model name")
  - status chip
  - a task list that ticks off as work happens, e.g. *narrate*: "Beat 3 of 8 · 4.2s"; *visuals*: "Capturing /dashboard", "Generating image 2 of 4"; *script*: "Drafting hook", "Covering feature 2"
  - live output for agents (the text they stream), collapsible, in a monospace panel
  - time, tokens and cost when finished
- Clicking a node scrolls to its card; clicking a card highlights its node.
- A **Cancel run** button stops the run at the next node boundary.

**Part 2: quality gates**
- Every hard check as a row with its real value and threshold:
  - "Duration · 59.4s · target 60s ±5% · ✅"
  - "Closing message present · ✅"
  - "Features covered · 3 of 3 · ✅"
  - "Narration pace · 152 wpm · 130–170 · ✅"
  - "Text fits templates · 0 overflows · ✅"
  - "Images present and sharp enough · ✅"
  - "Generated images in product UI scenes · 0 · ✅"
- The critic's rubric scores (hook, clarity, audience fit, storyline, call to action) as small bars, plus its verdict and reasons.
- If the critic fails the spec: the failed gates are marked, a before/after view shows exactly what `fix` changed, and the `recheck` results appear as "Attempt 2".
- If `recheck` fails, the run stops here with the report and an **Edit scenes** button instead of rendering.

**Part 3: the video**
- Appears when `render` finishes: a player with the final MP4, with the mascot in its "celebrating" pose beside it.
- **Download MP4** is the main button.
- Secondary downloads: brief (YAML), script and spec (JSON), and a zip of the whole run folder (images, audio, logs).
- **Edit and rerun** reopens the Brief or Scenes step with everything filled in.
- **Reveal in folder** opens the run folder on your machine.

**Run states**

| State | What the screen shows |
|---|---|
| queued | Position in the queue and a Cancel button |
| running | Live graph, cards and gates |
| waiting for approval | A banner with a button back to Script or Scenes |
| stopped | The `recheck` report and Edit scenes |
| failed | An error card with the node, the message and the fix (e.g. "ffmpeg not found: run `reelhive doctor`") |
| cancelled | What finished before cancelling, plus Rerun |
| done | Everything above, plus the video |

### 6.6 Runs

- A table of everything in the runs folder: thumbnail, name, date, level, provider, duration, status.
- Filter by status and provider; search by name.
- Opening a run **replays its Run screen from `run.log.jsonl`**, exactly as it looked live.
- Actions per run: open, duplicate as a new brief, download MP4, reveal in folder, delete (with a confirm dialog that names the folder).

### 6.7 Settings

**Providers**
- Agent provider for each tier (strong, fast): Claude, Bedrock, OpenAI, Ollama or Copilot. Per-node overrides behind an "Advanced" toggle.
- Model dropdowns filled from each provider: the Copilot list comes from the Copilot SDK's model listing, the Ollama list from the local Ollama server, the others from `config.yaml` defaults plus free text.
- Status per provider: key set / not set, AWS profile found, Ollama reachable, Copilot signed in (via `copilot` CLI login or a `GH_TOKEN` / `COPILOT_GITHUB_TOKEN` environment variable).
- **Test connection** per provider: a tiny prompt, showing latency or the exact error.
- Image generation: model and status of `OPENAI_API_KEY`.

**Defaults:** level, voice, format, music mood, credit placement.

**Storage:** runs folder path and disk usage.

**About:** ReelHive, Strands, Kokoro, Revideo and Copilot SDK versions, plus the full `reelhive doctor` output.

Settings write only non-secret values to `config.yaml`.

---

## 7. How events drive the Run screen

The event stream is defined in `core/events.py` (see `reelhive-plan.md`, 3.8). This is how the UI uses each event:

| Event | UI effect |
|---|---|
| `node.started` | Node turns to running; its card expands |
| `node.task` | A task line is added or ticked; progress counter updates |
| `agent.text` | Text appends to the card's live output (batched every 100ms) |
| `node.finished` | Node turns done or failed; time, tokens, cost shown |
| `node.skipped` | Node drawn dashed; card collapsed with "Skipped: critic passed" |
| `gate.result` | A row in the quality gates table fills in |
| `critic.verdict` | Rubric bars and verdict appear; the taken edge is highlighted |
| `fix.diff` | The before/after view appears under the gates |
| `run.finished` | The video part appears, or the stop report |

Replaying a past run feeds the saved events through the same store, so live and replayed runs use one code path.

---

## 8. API

All routes are under `/api` and require the launch token.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Server is up |
| GET | `/doctor` | Same checks as `reelhive doctor` |
| GET / PUT | `/settings` | Read and write non-secret settings |
| GET | `/providers/status` | Key, sign-in and reachability per provider |
| GET | `/providers/{name}/models` | Model list for one provider |
| POST | `/providers/{name}/test` | Test connection |
| POST | `/voices/preview` | Kokoro sample for voice + speed (cached) |
| GET | `/music` | CC0 library with moods and preview URLs |
| POST | `/briefs/validate` | Validate a brief; field errors on failure |
| POST | `/briefs/import` | YAML → brief |
| POST | `/briefs/export` | brief → YAML |
| POST | `/uploads` | Upload images into a run's working folder |
| POST | `/capture/test` | Capture routes now and return thumbnails |
| POST | `/login/start` | Open the visible sign-in browser |
| GET | `/login/status` | Waiting / signed in / failed |
| POST | `/runs` | Create a run from a brief and start the draft graph |
| GET | `/runs` | List runs |
| GET | `/runs/{id}` | Run details and current state |
| GET | `/runs/{id}/events` | Server-sent events, resumable with `Last-Event-ID` |
| POST | `/runs/{id}/script/regenerate` | Rewrite the script, optional note |
| POST | `/runs/{id}/script/approve` | Approve the script, with edits |
| PUT | `/runs/{id}/spec` | Save scene edits |
| POST | `/runs/{id}/scenes/{n}/regenerate` | Regenerate one scene, optional note |
| POST | `/runs/{id}/approve` | Approve scenes and start the production graph |
| POST | `/runs/{id}/cancel` | Cancel at the next node boundary |
| GET | `/runs/{id}/files/{name}` | Download an allow-listed file (MP4, brief, script, spec) |
| GET | `/runs/{id}/bundle.zip` | Whole run folder as a zip |
| POST | `/runs/{id}/reveal` | Open the run folder in the system file manager |
| DELETE | `/runs/{id}` | Delete a run folder, after the UI's confirm dialog |

---

## 9. Visual design

- **Feel:** a calm developer tool with character. Dense where it matters (cards, gates, logs), spacious around the video, and illustrated where it helps (section 10).
- **Colors:** the Mr.D brand: near-black and warm ivory as the base, with the acid-lime signal colour for "active" and primary actions. A honey amber appears only in the ReelHive logo mark. Exact values and type are aligned with SentryHive's and CostHive's look once those repos are shared.
- **Status colors** are always paired with an icon and a word, never color alone.
- **Typography:** one sans-serif for the interface, a monospace for agent output, specs and file names.
- **Motion:** only where it carries meaning (a running node pulses, a taken edge lights up, an agent's portrait gets a lime ring while it works), and switched off when the system asks for reduced motion.

---

## 10. Illustrations, icons and the Mr.D mascot

The UI should feel like a one-character studio: **Mr.D runs the whole production**, and every graph node is Mr.D in a different role. That matches the mascot's line on mr-d.dev, "Curious by nature. Always building."

### 10.1 The Mr.D mascot

The existing mascot, as shown on mr-d.dev and in the CostHive and SentryHive READMEs:
- a glossy, 3D vinyl-toy style character with a white sticker outline
- a black head shaped like the letter **D**, with a lime glow along its curved edge
- black glasses with lime-lit rims and glowing lime smiling eyes
- black hoodie with lime drawstrings, cargo pants with lime trim and a cloud patch, a backpack, and black sneakers with glowing lime soles

**Poses that exist today:** `mr-d-sticker` (standing, holding a laptop with a "D" on it) and `mr-d-walking`.

**Poses the UI needs**, each tied to a moment:

| Pose | Status | Where |
|---|---|---|
| Sticker (laptop) | exists | Sidebar footer and About tab, with "ReelHive by Mr.D" |
| Walking | exists | First launch, "Let's make a video" |
| Welcome (waving) | new | Empty Runs screen ("No videos yet") |
| Directing (director's megaphone) | new | Run screen header while a run is in progress |
| Thinking (hand on chin) | new | Waiting for approval (script or scenes) |
| Celebrating (arms up, confetti) | new | Next to the finished video and Download MP4 |
| Puzzled (head tilt, question mark) | new | Failed and stopped runs |
| Sleeping (sitting, "zzz") | new | Queued runs and "Reconnecting…" |

New poses are made from the existing artwork as reference (section 10.4), so the character stays identical. Once made, they are archived in S3 with the originals and handed to each project as files (section 10.6).

### 10.2 Agent portraits: Mr.D in every role

Each node is Mr.D with a role-specific prop or outfit detail, in the same vinyl-toy style:

| Node | Role | What Mr.D holds or wears |
|---|---|---|
| `brief` | Producer's assistant | Clipboard |
| `script` | Scriptwriter | Notebook and pen, pen behind the ear |
| `scenes` | Director | Storyboard frames, director's slate |
| `visuals` | Photographer | Camera around the neck, small paintbrush for generated images |
| `narrate` | Narrator | Studio microphone, headset |
| `music` | Composer | Big headphones, floating lime notes |
| `timing` | Timekeeper | Large stopwatch |
| `critic` | Critic | Magnifying glass and scorecard |
| `fix` | Fixer | Wrench, sleeves rolled up |
| `recheck` | Inspector | Checklist and stamp |
| `render` | Projectionist | Film reel, small projector |
| `suggest` *(M6)* | Editor | Sticky notes and a red pen |

- **Telling them apart at avatar size:** each prop has a distinct silhouette, portraits are cropped to head-and-prop for graph avatars, and the role name is always shown as text next to the portrait.
- **Where they appear:** on each agent card, on the graph nodes (as small round avatars), in the Settings "Advanced" per-node provider table, and in the docs page explaining the graph.
- **States without extra artwork:** one portrait per node, with state shown in CSS. Waiting is greyscale, running gets a pulsing lime ring (matching Mr.D's own glow), done gets a small check badge, failed gets a red badge, skipped is faded with a dashed outline.
- **Agent vs deterministic:** a small badge on the portrait ("AI" or "Tool"), so the image never hides how a node works.
- **Provider badge:** agent cards show the provider's name next to the portrait (Claude, Bedrock, OpenAI, Ollama, Copilot) as text, not third-party logos.

### 10.3 Illustrated icons

Illustrated icons share Mr.D's look: glossy black objects with lime glow edges, as if they came from his studio. They are used at **48px and larger**, where their detail reads well:

- sidebar section headers (New video, Runs, Settings), shown large when the sidebar is expanded
- the three level cards (small, medium, high)
- the visual source cards (auto, screenshots, your images, generate, none)
- the format cards (16:9, 9:16, 1:1)
- music mood cards
- provider tiles in Settings
- empty and error states (alongside the mascot)

Small functional icons (buttons, menus, status, toolbar, 16–24px) use **Lucide**, an MIT-licensed line icon set. At that size AI-generated icons look muddy and are harder to recognize, so they stay out of controls.

### 10.4 How the artwork is made

The artwork is generated with AI at design time and curated by hand. Nothing is generated while the app runs. The work is split by who reuses it:

| Artwork | Made in | Published to |
|---|---|---|
| Mascot poses and Mr.D role portraits | Dav's Mr.D brand work, since every project reuses them | archived in S3, provided to ReelHive as files in `assets/brand/` (10.6) |
| ReelHive's illustrated icons | ReelHive's own `design/` folder | committed to `ui/src/assets/icons/` |

Both use the same layout:
```
design/
├── style-guide.md           # Mr.D look: vinyl-toy 3D, sticker outline, near-black + lime glow, do / don't
├── prompts/
│   ├── _style.yaml          # shared style block added to every prompt
│   └── *.yaml               # mascot poses and roles (brand work), icons (ReelHive)
├── candidates/              # gitignored; raw generations to choose from
└── README.md                # how to add or regenerate an asset
scripts/generate_assets.py   # prompts + reference image → candidates
```

1. **Reference-based, not text-only.** Every mascot pose and agent portrait is generated from the existing `mr-d-sticker` artwork as a reference image (image editing with an input image), so the D-shaped head, glasses, glow and outfit stay the same. Text-only prompts drift too far from an existing character.
2. Generate 4 candidates per asset with `scripts/generate_assets.py`, which reuses the OpenAI image generator from the visuals step with reference-image support added.
3. Pick the best by hand and fix details if needed (the "D" on the laptop, glow placement, outline thickness).
4. Export as transparent WebP at 1x and 2x, plus a 1024px master. Mascot and role art is archived in S3 and provided to projects as files (10.6); icons are committed in ReelHive.
5. The new mascot poses come first; the agent portraits and icons follow, checked side by side against the existing two poses.

### 10.5 Asset rules

- **Both themes:** every asset has a transparent background with the white sticker outline, checked on both near-black and warm ivory.
- **Budget:** all illustration assets the UI ships together stay under 2 MB, are lazy-loaded below the fold, and are served as WebP.
- **Accessibility:** decorative art has empty alt text; agent portraits use the role name as alt text (e.g. "Mr.D as the Narrator"). Art never carries meaning on its own: every state also has text.
- **Disclosure:** the README and About tab say the illustrations were made with AI from the Mr.D artwork and curated by hand.
- **Licensing:** the Mr.D mascot in all poses and roles, the ReelHive logo and the Mr.D name are brand assets and are **not** covered by the code license. Their license file ships with them in `assets/brand/`; forks may use the code but must replace the brand assets. Only the non-mascot illustrated icons are released under the code license, so contributors can extend them.

### 10.6 Where the Mr.D files come from

- Dav provides the Mr.D files (mascot poses, role portraits, logos) as a set, with a `manifest.json` and the brand license. They are committed to `assets/brand/` at the repo root (layout in `reelhive-plan.md`, section 11).
- The originals are archived in a private S3 bucket. **Nothing in ReelHive loads from S3 or any other server**, at build time or run time.
- The UI imports the files from `assets/brand/` through a Vite alias, so the README and the UI use the same single copy.
- This keeps the UI fully offline and means opening the app never sends a request anywhere.
- CI checks that every pose and role the UI references exists and that every file matches its SHA-256 in `manifest.json`.

---

## 11. Accessibility

- Every action works with the keyboard; visible focus everywhere.
- WCAG AA contrast in both themes.
- Task updates are announced through a polite live region, throttled so screen readers aren't flooded.
- The graph has a text equivalent: the card list is the accessible version of the graph.
- All form fields have labels and inline error messages linked to the field.

---

## 12. Empty and error states

Each state pairs its message with a mascot pose or an illustrated icon (section 10), so empty and broken screens still feel like part of the app.

| Situation | What the UI says |
|---|---|
| No runs yet | Mascot "welcome" pose, "No videos yet", a button to start the first one, plus "Try an example brief" |
| No provider configured | Banner on New video: which variable to set or how to sign in to Copilot, with a link to Settings |
| Missing system dependency | Banner with the exact `reelhive doctor` finding and the install command |
| App URL unreachable in test capture | The URL, the error, and "Is your dev server running?" |
| Sign-in window closed early | "Sign-in cancelled", with Try again |
| Upload rejected | File name and reason (type or size) |
| Server restarted mid-run | The run is marked interrupted, with Resume from the last finished node |
| Browser loses connection | "Reconnecting…", then the stream resumes from the last event ID |

---

## 13. Folder structure

```
src/reelhive/server/
├── app.py                # FastAPI app, static files, startup token
├── security.py           # bind check, token, Host + Origin checks
├── deps.py               # shared dependencies (service, settings)
└── routes/
    ├── health.py
    ├── settings.py
    ├── providers.py
    ├── voices.py
    ├── music.py
    ├── briefs.py
    ├── uploads.py
    ├── capture.py
    ├── login.py
    ├── runs.py           # runs, approvals, regen, cancel, events, files
    └── (agui.py)         # M6: AG-UI endpoint for the suggest agent (section 16)

ui/
├── README.md
├── package.json
├── vite.config.ts
├── src/
│   ├── main.tsx
│   ├── app/              # router, layout, theme, top bar
│   ├── api/              # generated client + query hooks
│   ├── stores/           # run event store (Zustand)
│   ├── pages/
│   │   ├── NewVideo/     # stepper: Brief, Visuals, Script, Scenes
│   │   ├── Run/
│   │   ├── Runs/
│   │   └── Settings/
│   ├── components/
│   │   ├── LevelSwitch, VoicePicker, FeatureList, FormatPicker
│   │   ├── CaptureTester, ImageGrid, MaskEditor
│   │   ├── BeatCard, SceneTimeline, ScenePanel, ScenePreview
│   │   ├── GraphView, AgentCard, TaskList, LiveOutput
│   │   ├── GateTable, RubricBars, FixDiff
│   │   ├── VideoResult, DownloadMenu
│   │   ├── SuggestionChips              # M6, CopilotKit (section 16)
│   │   └── Mascot, AgentPortrait, Illustration
│   ├── assets/
│   │   └── icons/        # illustrated icons (non-mascot), WebP 1x + 2x
│   │                     # Mr.D files come from the repo-root assets/brand/ via a Vite alias
│   └── schemas/          # Zod schemas generated from Pydantic
└── tests/
    ├── components/       # vitest + Testing Library
    └── e2e/              # Playwright
```

---

## 14. Tests

| Layer | Tool | What it covers |
|---|---|---|
| API | pytest + FastAPI TestClient | Every route calls `core/service.py`; approvals, regen and cancel give the same results as the CLI |
| Security | pytest | Missing or wrong token, foreign `Host`, foreign `Origin`, path tricks on downloads and uploads are all rejected; the server refuses to bind beyond 127.0.0.1 |
| Events | pytest | SSE resumes correctly from `Last-Event-ID`; replaying `run.log.jsonl` gives the same store state as live |
| Components | vitest + Testing Library | Level switch shows the right fields; validation errors land on the right field; graph view, agent cards, gate table and fix diff follow events |
| Accessibility | axe in vitest and Playwright | No violations on every screen in both themes |
| Assets | vitest + pytest | Every graph node has a role portrait; every mascot pose referenced in code exists; every asset has a 2x version; brand files match the SHA-256 in `assets/brand/manifest.json`; the total size stays under 2 MB |
| Visual snapshots | Playwright screenshots | Run screen, empty states and agent cards in light and dark themes, compared against stored snapshots |
| End to end | Playwright | Full medium run (form → approve script → watch agents and gates → play video → download MP4 and zip); a forced failure that stops at `recheck`; reconnect mid-run; import and export a brief. All against the fake model, fake TTS and the fixture site |

All UI tests run in CI on every push, with no API keys.

---

## 15. Done when (milestone M3 in the main plan)

- Every screen in section 6 works at all three levels.
- A brief made in the UI and the same brief run with the CLI produce identical `spec.json` files.
- A past run reopens and replays exactly as it ran.
- All security tests pass, and the UI cannot be reached from another machine.
- Accessibility checks pass in light and dark themes.
- The Mr.D mascot appears in all poses from 10.1, every node has its Mr.D role portrait, and the illustrated icons from 10.3 are in place; brand files in `assets/brand/` are verified against their manifest.
- `ui/README.md` covers running, dev mode and adding a screen.

## 16. Later phase: AI quick actions with CopilotKit (M6, learning goal)

**Not part of the first release.** This is milestone M6 in the main plan, after v0.1.0. Its purpose is partly to learn generative UI and agent-driven suggestions with CopilotKit, alongside Strands Graph and the GitHub Copilot SDK. Backend design: `reelhive-plan.md`, section 3.10.

> **CopilotKit is not the GitHub Copilot SDK.** CopilotKit is an open-source React framework for in-app AI and generative UI (the makers of the AG-UI protocol), used here in the frontend. The GitHub Copilot SDK is the agent runtime behind one of the five providers, used in the backend. The UI, code and docs always name them in full.

### 16.1 What the user sees

**Script screen (6.3):** under each beat card, a row of 3–4 suggestion buttons for that beat, e.g. "Punchier hook", "Cut to one sentence", "Mention feature 2".

**Scenes screen (6.4):** in the detail panel of the selected scene, a row of 3–4 suggestion buttons, e.g. "Shorten by ~2s", "Simpler on-screen text", "Stronger call to action", "Use the dashboard screenshot".

- Suggestions are specific to that beat or scene, never a generic list.
- Each button shows a short label; hovering or focusing it shows the full instruction behind it.
- One click regenerates only that beat or scene, with the instruction as the note. The beat or scene shows "Applying…", then the new version, with **Undo** to go back to the previous one.
- A small "More ideas" button asks for a fresh set.
- Suggestions appear with Mr.D as the **Editor** (sticky notes and a red pen), the twelfth role portrait (section 10.2), so it's clear an agent wrote them.
- **No chat box and no free-text input** in this phase.

### 16.2 How it works

```
Script / Scenes screen
  └─ CopilotKit provider
       ├─ useCoAgent("suggest")      shares the selected beat or scene + brief with the agent
       └─ useCopilotAction("propose_suggestions", render → SuggestionChips)
                │  AG-UI over the same local server, token required
                ▼
FastAPI  /api/agui/suggest  (server/agui.py, community Strands ↔ AG-UI integration)
                ▼
Strands agent `suggest` (fast tier)  ──►  propose_suggestions([{label, instruction}, …])

Click a chip  ──►  POST /api/runs/{id}/scenes/{n}/regenerate  { note: instruction }
                   (or /script/regenerate for a beat)  ──►  core/service.py
```

- **Generative UI:** the agent's `propose_suggestions` tool call is rendered by CopilotKit as the `SuggestionChips` component. That's the part of CopilotKit this phase is meant to teach.
- **The agent only suggests.** Applying a suggestion always goes through the existing regenerate routes and `core/service.py`, so the spec, the run log and the CLI stay in sync.
- **When suggestions are fetched:** when a beat or scene is selected, not for all of them at once. They're cached per version of that beat or scene, so going back and forth costs nothing.
- **Events:** `suggestion.offered` and `suggestion.applied` appear in the event stream and the run log; the Run screen's history shows which suggestions shaped the video.
- **Providers:** works with the Strands-based providers in this phase. If the user's provider is the Copilot SDK, the buttons are hidden with a note in Settings, until the follow-up adds Copilot SDK support.
- **Security:** the AG-UI endpoint sits behind the same launch token, Host and Origin checks as every other route (section 4).
- **CopilotKit runtime:** if the pinned CopilotKit version needs its own Node runtime process between the browser and the AG-UI endpoint, `reelhive ui` starts it on 127.0.0.1 with the same token checks. To confirm when the phase starts.

### 16.3 Settings

- **AI quick actions:** on / off (default on once M6 ships), and how many suggestions to show (3 or 4).
- The provider and model follow the `fast` tier, with an override in the Advanced per-node table.

### 16.4 Additions to the API, folders and tests

| Area | Addition |
|---|---|
| API | `POST /agui/suggest` (AG-UI endpoint); existing regenerate routes reused for applying; `POST /runs/{id}/scenes/{n}/undo` and `/script/beats/{n}/undo` |
| Server | `server/agui.py` wraps the community integration in one module |
| UI | `components/SuggestionChips`, a CopilotKit provider around the Script and Scenes pages only |
| Assets | Mr.D **Editor** role portrait added to the brand set |
| Tests | Components: chips render from a mocked `propose_suggestions` call, clicking sends the right note, Undo restores the previous version. API: the AG-UI endpoint rejects missing tokens and foreign `Host`/`Origin`. End to end: open Scenes, click "Shorten by ~2s", check the scene got shorter, Undo. All with the fake model. |
| Docs | `docs/copilotkit.md`: AG-UI, `useCoAgent`, `useCopilotAction`, and how the quick actions are wired, written as learning notes |

### 16.5 Done when

- Script and Scenes show 3–4 specific suggestions for the selected beat or scene.
- One click regenerates only that beat or scene, and Undo works.
- The AG-UI endpoint passes all security tests.
- CopilotKit is limited to the Script and Scenes pages, so removing it would touch only those components.
- `docs/copilotkit.md` explains the whole flow.

### 16.6 Even later

A conversational "edit by talking" mode, using CopilotKit's sidebar so the user can type "shorten scene 3 and make the hook punchier", could grow out of the same `suggest` agent and AG-UI endpoint. It's noted as a possibility only; it isn't planned.

---

## 17. Open UI questions

1. Default port: random free port (proposed, avoids clashes) or a fixed one such as 8765.
2. Whether "Reveal in folder" and "Delete run" should be hidden behind Settings for extra safety, or stay on each run (proposed: stay, with a confirm on delete).
3. Whether the original source files of the Mr.D artwork (higher resolution than the 480px WebPs on mr-d.dev) are available as the reference for new poses. Better references give more faithful poses.
4. M6: confirm whether the pinned CopilotKit version can talk to the FastAPI AG-UI endpoint directly or needs its own local Node runtime process (section 16.2).

**Decided:** the mascot exists (mr-d.dev, CostHive and SentryHive READMEs); every agent is Mr.D in a role, no separate characters; Mr.D originals are archived in S3, and each project gets its own committed copy of the files; nothing loads from S3.
