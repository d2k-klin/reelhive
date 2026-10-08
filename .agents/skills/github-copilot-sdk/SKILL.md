---
name: github-copilot-sdk
description: "Integrate, secure, debug, or test applications using the GitHub Copilot SDK, including sessions, model listing, streaming events, custom tools, structured output, authentication, permissions, runtime setup, and fake sessions. Use when working with github-copilot-sdk or embedding Copilot's agent runtime."
---

# GitHub Copilot SDK

Use this workflow when an application embeds the Copilot agent runtime rather than calling an LLM API directly.

## Procedure

1. Inspect the pinned SDK version, installed type information, and official examples before choosing API names; the SDK evolves quickly.
2. Treat each unit of work as a bounded session with an explicit system prompt, model selection, timeout, and cleanup path.
3. Prefer structured output through one or more application-owned tools whose parameter schemas come from the application's canonical models.
4. Validate tool arguments again at the application boundary. A successful tool call is not a substitute for domain validation.
5. Translate SDK streaming events into application-level events; do not leak SDK event objects through the rest of the codebase.
6. Centralize authentication and runtime discovery. Support only documented token and signed-in CLI flows, and never print credentials.
7. Close sessions and child processes on success, failure, cancellation, and timeout.

## Permission Boundary

- Start from deny-all.
- Enable only application-owned tools required for the task.
- Reject shell, filesystem, network, and editor actions unless the product explicitly needs and audits them.
- Treat prompts, tool arguments, and streamed text as untrusted input.

## Testing

- Use a fake session behind the same adapter as the real SDK.
- Cover valid tool output, malformed arguments, no tool call, permission denial, timeout, cancellation, and stream ordering.
- Include a test proving forbidden built-in actions are rejected.
- Keep SDK/network tests separate and opt-in.

## Done When

The SDK is isolated behind an adapter, structured output is validated, permissions are least-privilege, lifecycle cleanup is deterministic, and normal tests require neither Copilot sign-in nor network access.