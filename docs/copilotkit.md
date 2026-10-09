# Learning notes: AI quick actions with CopilotKit (M6)

M6 is a learning goal: CopilotKit, AG-UI, a Strands-backed agent and the GitHub Copilot SDK in one project. Two different "Copilots" are involved and are never mixed up:

| | CopilotKit | GitHub Copilot SDK |
| --- | --- | --- |
| What it is | An open-source React framework for in-app AI and generative UI; makers of the AG-UI protocol | GitHub's SDK for running the Copilot agent runtime |
| Where it sits | The studio's frontend (Script and Scenes screens only) | The backend, as one of the five agent providers |
| ReelHive uses it for | Rendering suggestion buttons from an agent's tool call | Running agent nodes on a Copilot subscription |

## What the user sees

On the Script screen, the selected beat shows 3-4 buttons written for it ("Punchier hook", "Shorten by ~2s", ...). On the Scenes screen, the selected scene shows its own. Hovering or focusing a button shows the instruction behind it. One click regenerates only that beat or scene with the instruction as the note; **Undo last change** restores the previous version, and **More ideas** asks for a fresh set. There is no chat box. Settings has an on/off switch.

## How it works

```
Script / Scenes screen
  └─ QuickActions (lazy-loaded; the only place CopilotKit is imported)
       ├─ CopilotKitProvider  selfManagedAgents={{suggest: new HttpAgent({url: '/api/agui/suggest'})}}
       ├─ useAgent('suggest')         agent.setState({run_id, target, index, fresh}) + copilotkit.runAgent()
       └─ useFrontendTool('propose_suggestions', zod schema, handler → buttons)
                │  AG-UI over SSE, same server, launch token + Host + Origin checks
                ▼
FastAPI  POST /api/agui/suggest  (src/reelhive/server/agui.py)
   └─ Service.suggest()  →  validated Suggestions (3-4, distinct), cached per beat/scene version,
                            `suggestion.offered` in run.log.jsonl
   └─ streams RUN_STARTED · TOOL_CALL_START(propose_suggestions) · TOOL_CALL_ARGS · TOOL_CALL_END · RUN_FINISHED

Click a button  ──►  POST /api/runs/{id}/script/regenerate  {note, suggestion, beat}
                     POST /api/runs/{id}/scenes/{n}/regenerate {note, suggestion}
                     ──► core/service.py: saves the previous version, regenerates, emits `suggestion.applied`
Undo            ──►  POST /api/runs/{id}/script/undo  |  /scenes/{n}/undo  ──► `version.restored`
```

## Decisions and what we learned

- **No CopilotKit runtime process (open decision 5).** CopilotKit 1.74's `CopilotKitProvider` accepts AG-UI agents directly through `selfManagedAgents`, so the browser talks to the FastAPI endpoint with `@ag-ui/client`'s `HttpAgent`. `reelhive ui` stays one Python process on 127.0.0.1.
- **v2 hooks.** The plan named `useCoAgent` and `useCopilotAction`; in CopilotKit 1.74 they are deprecated in favour of `useAgent` (shared state and runs) and `useFrontendTool` (a tool the agent calls and the browser executes and renders). Same idea, current API.
- **Generative UI from a validated call, not a free-running loop.** The endpoint streams the tool call from `Service.suggest()` instead of letting an agent loop decide. That keeps the plan's guarantees: suggestions are validated (3-4, distinct, bounded lengths), cached per version of the beat or scene, logged, and identical to `reelhive suggest` in the CLI. The browser validates the arguments again with zod before rendering anything. We used the official `ag-ui-protocol` events directly; the community `ag-ui-strands` adapter (which wraps a whole Strands agent loop) wasn't needed for a single deterministic tool call.
- **The agent only proposes.** Applying always goes through the existing regenerate routes and `core/service.py`, which keep the previous version (`runs/<run>/versions/`) for undo. The CLI has the same actions: `reelhive suggest <run> --beat 1 --apply 2`, `reelhive undo <run> --script`.
- **Pinned and quiet.** `@copilotkit/react-core` 1.74.0 with the `@ag-ui/client` 0.0.59 it was built against, and `ag-ui-protocol` 0.1.22, all at least two weeks old when pinned. CopilotKit pulls in `@scarf/scarf` install analytics; the root `package.json` disables it (`scarfSettings.enabled: false`). A Playwright test asserts the studio makes no request outside 127.0.0.1 while using quick actions.
- **Providers.** Suggestions run on the Strands providers (Claude, Bedrock, OpenAI, Ollama) at the fast tier. With GitHub Copilot as the provider, the endpoint returns a clear AG-UI `RUN_ERROR` and the buttons show it; running `suggest` on the Copilot SDK is a follow-up.
- **A bug found on the way.** Testing the Scenes screen showed that React 19 sets props on custom elements as properties, and Revideo's `<revideo-player>` has a getter-only `variables`, so every preview update blanked the page. `ui/src/revideo-player-fix.ts` adds the missing setter; an error boundary now shows a message instead of a blank screen.

## Tests

- `tests/unit/test_agui.py`: the AG-UI stream and its event order, caching and "More ideas", a quiet finish after the tool result, bad state as `RUN_ERROR`, the same token/Host/Origin security as every route, apply with `suggestion.applied`, undo for the script and a scene.
- `ui/src/components/suggestions.test.ts`: malformed `propose_suggestions` arguments are rejected.
- `ui/tests/e2e/quick-actions.e2e.ts`: against the real server with a fake model, the buttons render, apply and undo work for a beat and a scene, "More ideas" refreshes, nothing leaves 127.0.0.1, and axe passes.
- `tests/integration/test_eval_run.py`: the evals score quick actions (specific, label fidelity, variety, safe) with `evals/rubrics/suggestions.md`.

## Even later

A conversational "edit by talking" mode (CopilotKit's sidebar, typing "shorten scene 3 and make the hook punchier") could grow out of the same agent and endpoint. It is only an idea.
