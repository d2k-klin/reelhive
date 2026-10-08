---
name: copilotkit-ag-ui
description: "Design, integrate, secure, or test CopilotKit and AG-UI generative interfaces, including useCoAgent, useCopilotAction, shared state, tool-call rendering, Strands or other agent backends, local endpoints, approvals, undo, event logging, and provider boundaries."
---

# CopilotKit + AG-UI

Use this workflow when an agent proposes or renders application UI through AG-UI.

## Procedure

1. Confirm the pinned CopilotKit and AG-UI integration versions and whether the chosen backend can connect directly or requires a runtime process.
2. Define a narrow agent contract with typed shared state and a small set of application-specific tools.
3. Use `useCoAgent` only for the selected workflow context; avoid exposing an entire application state tree to the agent.
4. Use `useCopilotAction` to render typed tool calls as real components. Validate arguments before rendering or applying them.
5. Separate proposing from mutating. Agent output should become a reviewable suggestion; application services remain the authority for changes.
6. Route accepted actions through existing application commands or APIs so validation, authorization, logging, and non-AI clients stay consistent.
7. Persist the previous version before applying a suggestion and provide an explicit undo path.
8. Log offered, accepted, rejected, and undone actions with enough context to audit behavior without storing secrets.

## Security and Cost

- Put AG-UI endpoints behind the same authentication, Host, Origin, and rate limits as the rest of the application.
- Treat tool labels, instructions, and rendered text as untrusted content.
- Cache suggestions by canonical input version and generate only for visible or requested content.
- Make provider/model selection explicit and report unavailable providers without silently switching.

## Testing

- Mock the AG-UI stream and tool calls in component tests.
- Assert malformed tools cannot render or mutate state.
- Test apply, failure, retry, undo, cache reuse, reconnect, and security headers.
- Keep live-provider tests opt-in.

## Done When

The agent proposes bounded typed actions, the application owns mutations, undo is reliable, endpoint security matches the host application, and tests run without a live model.