# Copilot as an agent provider

The [GitHub Copilot Python SDK](https://github.com/github/copilot-sdk/tree/main/python) runs its own local agent runtime. ReelHive's `CopilotAgentNode` implements the same `MultiAgentBase` contract as the Strands-backed nodes; graph topology and application validation do not depend on the provider.

Each invocation opens one session with the node's system prompt and exactly one `submit_<node>` tool. Its parameters come from the same Pydantic output schema used by Strands. The tool validates its arguments before applying any changes. Invalid output is returned as a tool failure and receives one explicit repair turn if the session finishes without a valid submission.

`available_tools` allows only the submit tool. Its handler has no external side effects and bypasses permissions; every permission request from the runtime is denied. Config discovery, custom instructions, skills, file hooks, host Git operations and session storage are disabled. Streaming deltas become `agent.text` events, usage becomes node token counts, and sessions and clients are closed even on failure.

Unit tests use `FakeCopilotSession` to verify output, repair, streaming and shell/file-write denial without credentials. Live account/model access still depends on the user's subscription and runtime authentication. CopilotKit belongs to M6 and is not involved in this integration.
