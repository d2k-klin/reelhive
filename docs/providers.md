# Providers

Set `provider` and `models.<provider>.strong/fast` in `config.yaml`. The strong tier runs script, critic and fix; the fast tier runs scenes and music. Model names for non-Claude providers must be configured explicitly. `config.example.yaml` shows every field.

| Provider | Setup | Authentication |
| --- | --- | --- |
| Claude | Installed by default | `ANTHROPIC_API_KEY` |
| Bedrock | Installed by default | Standard AWS credentials/profile and region |
| OpenAI | `uv sync --extra openai` | `OPENAI_API_KEY` |
| Ollama | `uv sync --extra ollama` and pull your models | Local server at `ollama_host` |
| GitHub Copilot | `uv sync --extra copilot` | Copilot CLI sign-in, `GH_TOKEN` or `COPILOT_GITHUB_TOKEN` |

```yaml
provider: claude
nodes:
  script: copilot
  scenes: ollama
models:
  claude: {strong: claude-sonnet-5-5, fast: claude-haiku-5-5}
  copilot: {strong: YOUR_COPILOT_MODEL_ID, fast: YOUR_COPILOT_MODEL_ID}
  ollama: {strong: YOUR_INSTALLED_MODEL, fast: YOUR_INSTALLED_MODEL}
```

Run `reelhive models --provider copilot` for the account's live model list. Other providers show configured models. `reelhive doctor --config config.yaml` checks the selected providers, local dependencies, and Copilot runtime/sign-in when selected. It does not make a paid model request. Ollama with generation and image descriptions disabled makes no cloud model calls.

`make setup EXTRAS="--extra copilot --extra openai --extra ollama"` installs all integrations and prefetches the Copilot runtime. The SDK is pinned to 1.0.17; it downloads its matching runtime on first use if needed. Never pass credentials in committed config files.

The CLI saves the selected config in the run directory. `reelhive approve <run-folder>` uses it to resume without regenerating the script. Invalid structured output gets one explicit repair attempt after the provider's own validation handling; repeated failure stops the run.
