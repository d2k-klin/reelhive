# `docs`

**Overview.** Everything you need to use, understand and extend ReelHive, beyond the README, which stays a short overview. Start with the architecture, then read whichever guide matches what you're doing.

## Using ReelHive

| Doc | Read it for |
| --- | --- |
| [getting-started.md](getting-started.md) | Install, first video, customization levels, every command |
| [studio.md](studio.md) | A short tour of the studio and its quick actions |
| [ui-guide.md](ui-guide.md) | The studio, screen by screen, with screenshots |
| [brief-reference.md](brief-reference.md) | Every brief field, by level, with defaults |
| [visuals.md](visuals.md) | Provided images, screenshots with login and masking, generation, fallbacks, privacy |
| [providers.md](providers.md) | Claude, Bedrock, OpenAI, Ollama and Copilot; per-node overrides |
| [templates.md](templates.md) | Templates and their character limits |
| [limits.md](limits.md) | Every enforced limit, voices and formats |
| [privacy.md](privacy.md) | What leaves your machine, and the ReelHive credit |

## Understanding it

| Doc | Read it for |
| --- | --- |
| [architecture.md](architecture.md) | The graphs, nodes, hard checks, render contract, run folder and events |
| [strands-graph.md](strands-graph.md) | Learning notes: custom nodes, OR-joins, conditional edges, state |
| [copilot-sdk.md](copilot-sdk.md) | Learning notes: GitHub Copilot as a locked-down provider |
| [copilotkit.md](copilotkit.md) | Learning notes: quick actions with CopilotKit and AG-UI (M6) |

## Extending it

| Doc | Read it for |
| --- | --- |
| [adding-a-template.md](adding-a-template.md) | A new scene template, end to end |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | Dev setup, where things go, the prompt gate |
| [../evals/README.md](../evals/README.md) | Running and reading evals |

## Planning

| Doc | What it is |
| --- | --- |
| [plan.md](plan.md) | The project plan, milestones and what each one delivered |
| [reelhive-ui-plan.md](reelhive-ui-plan.md) | The local UI plan (M3) |

## Extending the docs

One topic per file, and link it from this index (and from the root README's documentation table if it's a main guide). Keep the root README short and free of tool names. Every folder also has its own README for the code in it. Relative links are checked by `tests/unit/test_docs.py`.
