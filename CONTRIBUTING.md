# Contributing to ReelHive

Thanks for helping turn briefs into good videos.

## Dev setup

```bash
make setup                                  # uv sync, Playwright Chromium, npm ci, headless Chrome
make test                                   # pytest (fakes only) + renderer vitest
make lint                                   # ruff, mypy, tsc
make test-slow                              # real Kokoro + real Revideo render (optional)
```

The default suite needs **no API keys and no internet**: agents run on `FakeModel`, Copilot on `FakeCopilotSession`, images on `FakeImageGenerator`, and screenshots against a fixture site served on 127.0.0.1. Keep it that way; anything that needs the network or a real model belongs behind `@pytest.mark.slow` or in `evals/`.

## Where things go

- **A new agent node or a graph change:** read [docs/strands-graph.md](docs/strands-graph.md) first. Nodes subclass `FunctionNode` (deterministic) or `AgentNode` (LLM with validated structured output) in `src/reelhive/nodes/base.py`. Every node must emit `node.started` / `node.finished`; long work emits `node.task`.
- **A new template:** [docs/adding-a-template.md](docs/adding-a-template.md). Change the Pydantic model first, run `make schema`, then write the renderer component. The contract test fails until both sides agree.
- **A new provider:** `src/reelhive/providers/factory.py`. The graph must not know which provider is in use.
- **Music:** CC0 only, with source and license in `assets/music/manifest.json`. See [assets/music/README.md](assets/music/README.md).

## Prompt changes are gated

Editing anything in `src/reelhive/agents/prompts/`, `evals/rubrics/` or `evals/datasets/` triggers the eval gate: the core set on Claude may not regress by more than 5% against `evals/baselines/claude-core.json`. Run `uv run reelhive eval --providers claude --set core --baseline evals/baselines/claude-core.json` locally first. If a change is an intended trade-off, refresh the baseline in the same PR with `make eval-baseline` and say why. See [evals/README.md](evals/README.md).

## Pull requests

- Conventional commits (`feat:`, `fix:`, `docs:`, `ci:`, `deps:` ...).
- Tests and docs in the same PR; a `CHANGELOG.md` entry under `[Unreleased]`.
- Never commit API keys, `auth.json` login state, or run folders. `runs/`, `config.yaml` and `auth.json` are gitignored for a reason.
- The Mr.D brand assets in `assets/brand/` are not covered by the code license. Forks keep the code and replace them.
