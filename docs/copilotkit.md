# Learning notes: AI quick actions with CopilotKit (M6)

M6 is a learning goal: CopilotKit, a Strands agent and the GitHub Copilot SDK in one project. Two different "Copilots" are involved and are never mixed up:

| | CopilotKit | GitHub Copilot SDK |
| --- | --- | --- |
| What it is | An open-source React framework for in-app AI and generative UI; makers of the AG-UI protocol | GitHub's SDK for running the Copilot agent runtime |
| Where it sits | The local UI's frontend | The backend, as one of the five agent providers |
| ReelHive uses it for | Rendering suggestion buttons | Running agent nodes on a Copilot subscription |

## The feature

On the Script screen (per beat) and the Scenes screen (per scene), the user sees 3-4 buttons written by an agent for that beat or scene, such as "Punchier hook", "Shorten by ~2s", "Simpler wording" or "Stronger call to action". One click regenerates that beat or scene with the suggestion's instruction as the note. It is buttons, not a chat box.

## What exists now

The backend half, which does not depend on the UI:

- **`suggest` agent** (`src/reelhive/agents/suggester.py`, prompt `agents/prompts/suggester.md`): a Strands agent on the provider's fast tier. It receives the brief, the whole script for context, and one beat or scene, and returns a validated `Suggestions` object: 3-4 items, each with a `label` (≤28 characters, distinct) and an `instruction` (the note). It is not a graph node; it runs on demand while a run is paused.
- **Cache per version:** the cache key is a hash of the exact beat or scene, so suggestions are reused until that beat or scene changes, and each version gets its own (`runs/<run>/suggestions/<beat|scene>_NN_<hash>.json`).
- **Events:** `suggestion.offered` (target, index, version, cached, tokens, the suggestions) goes into `run.log.jsonl` like every other event; `suggestion.applied` is reserved for the regenerate path.
- **CLI:** `reelhive suggest <run-folder> --beat 2` or `--scene 3` prints the same suggestions the UI will show.
- **Providers:** Claude, Bedrock, OpenAI and Ollama. Running `suggest` on the Copilot SDK is a follow-up, and a good test of the two "Copilots" side by side.

## What lands with the M3 UI

These pieces plug into M3's FastAPI server and React UI, so they're built on top of M3, not beside it:

1. **AG-UI endpoint:** expose the `suggest` agent through the community Strands ↔ AG-UI integration, wrapped in one module (`server/agui.py`) with a pinned version, and mounted in the FastAPI app behind the same launch token, Host and Origin checks as every other route.
2. **CopilotKit in the UI:** `useCoAgent` shares the selected beat or scene with the agent; the agent's `propose_suggestions` tool is rendered with `useCopilotAction` as the row of buttons. That is CopilotKit's generative UI: the agent's tool call becomes real components. The components stay isolated, so CopilotKit can be removed without touching the rest of the UI.
3. **Applying goes through the existing path:** a click calls `/runs/{id}/script/regenerate` or `/runs/{id}/scenes/{n}/regenerate` with the instruction as the note, and emits `suggestion.applied`. The agent never edits the spec itself; `core/service.py` owns every change and keeps the previous version, so each applied suggestion can be undone. The CLI gets `reelhive suggest --apply N`.
4. **Evals:** a judge metric that each suggestion is specific to its beat or scene, and that applying it does what the label says ("Shorten by ~2s" really shortens it).

Open decision 5 still applies: whether CopilotKit can talk to the AG-UI endpoint in FastAPI directly or needs its own Node runtime process, which `reelhive ui` would then start on 127.0.0.1 with the same token checks.
