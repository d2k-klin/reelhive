# `providers/copilot`

**Overview.** GitHub Copilot as an agent provider. Copilot is not a model that Strands can call: the Copilot SDK runs Copilot's own agent runtime locally over JSON-RPC. So `AgentNode` hands its work to `CopilotAgentNode`, which keeps the same graph contract, prompts and output models.

## What's here

| File | What it is |
| --- | --- |
| [`node.py`](node.py) | `CopilotAgentNode`: opens one session per node run with the node's prompt and exactly one `submit_<node>` tool whose parameters are the output model's JSON Schema; validates the submitted arguments; gives one repair turn; turns message deltas into `agent.text` and usage into token counts; always closes the session and client. Also `deny_permission`, `list_models()` (for `reelhive models`) and `auth_status()` (for `doctor`). |

## Security model

Copilot's runtime can run shell commands and edit files, so every session is locked down. `available_tools` contains only the submit tool, and every permission request is denied. Config discovery, custom instructions, skills, file hooks, host Git operations, session storage and MCP servers are all off. `tests/unit/test_providers.py` proves that shell and file-write requests are refused, using `FakeCopilotSession`, with no account needed.

## Extending

- **Running another node on Copilot** needs nothing here: set `nodes: {<node>: copilot}` in `config.yaml`.
- **Running `suggest` on Copilot** (an M6 follow-up): call `CopilotAgentNode` with a small adapter exposing `name`, `prompt`, `output`, `build_prompt` and `apply`, and lift the `ProviderError` in `Service.suggest`.
- **SDK upgrades:** the SDK is pinned (`github-copilot-sdk==1.0.17`) because session options change between versions. Bump it deliberately and rerun the provider tests.

See also: [docs/copilot-sdk.md](../../../../docs/copilot-sdk.md).
