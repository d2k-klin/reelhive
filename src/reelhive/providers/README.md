# `providers`

**Overview.** Decides which model runs each agent. The graph never knows: it asks for the `strong` or `fast` tier (or a per-node override), and this folder turns `config.yaml` into the matching Strands model, or into a Copilot SDK session for GitHub Copilot.

## What's here

| Path | What it is |
| --- | --- |
| [`factory.py`](factory.py) | `build_model(config, provider, tier)` for Claude (`AnthropicModel`), Bedrock (`BedrockModel`), OpenAI (`OpenAIModel`) and Ollama (`OllamaModel`); `build_models(config)` for the default tiers plus per-node overrides; `NODE_TIERS`; `ProviderError` with install hints. |
| [`copilot/`](copilot) | GitHub Copilot through the Copilot SDK, which plugs in at node level, not model level. |

Tiers: **strong** runs `script`, `critic` and `fix`; **fast** runs `scenes`, `music` and `suggest`. Model names come only from `config.yaml` (defaults: `claude-sonnet-5-5` / `claude-haiku-5-5`); `config.example.yaml` shows every field.

## Extending: a new Strands-backed provider

1. Add the name to the `Provider` literal in [`../config.py`](../config.py).
2. Add a branch in `build_model` that imports the Strands model class lazily, so a missing extra gives a clear `ProviderError`.
3. Add an optional extra in `pyproject.toml` if it needs a package, and a row in [docs/providers.md](../../../docs/providers.md).
4. Test it in `tests/unit/test_providers.py` the way the others are tested: monkeypatch the class and assert the configured model id is passed.
5. Compare it against the others with `reelhive eval --providers claude,<new>`.

A provider that is not a Strands model (like Copilot) needs its own node runner; see [`copilot/README.md`](copilot/README.md).
