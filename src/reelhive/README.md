# `reelhive` (the Python package)

**Overview.** Everything that turns a brief into a video, except the frame renderer (which is Node, in [`renderer/`](../../renderer)). The CLI is a thin layer over [`core/service.py`](core/service.py), which drives two Strands graphs built from the nodes and agents in this package.

## What's here

| Path | What it is |
| --- | --- |
| [`cli.py`](cli.py) | Typer CLI: `init`, `run`, `approve`, `approve-scenes`, `regen`, `resume`, `preview`, `ui`, `doctor`, `voices`, `login`, `capture`, `models`, `eval`, `suggest`, `publish`, `connect`, `accounts`, `disconnect`. Parses arguments, prints progress, calls the service. No logic of its own. |
| [`config.py`](config.py) | `config.yaml` model (provider, models per tier, per-node overrides, image generation, publishing) and `REPO_ROOT`. |
| [`levels.py`](levels.py) | What each customization level fills from defaults and where it pauses for approval. |
| [`doctor.py`](doctor.py) | The checks behind `reelhive doctor` (Python, Node, browsers, ffmpeg, espeak-ng, Kokoro, keys, Copilot, credit). |
| [`core/`](core) | The service, the workspace (jobs for the UI), the run context with checkpoints, and the event stream. Start reading here. |
| [`server/`](server) | The loopback-only FastAPI app behind `reelhive ui`. |
| [`graphs/`](graphs) | The draft, production and publishing Strands graphs: just topology. |
| [`nodes/`](nodes) | Deterministic graph nodes plus the `FunctionNode` / `AgentNode` base classes. |
| [`agents/`](agents) | LLM nodes (research, script, scenes, music, critic, fix, review, sound, publish) and the on-demand `suggest` agent, with their prompts. |
| [`schemas/`](schemas) | Pydantic models: the brief, the script, the scene spec (the render contract), the layout report and publishing. |
| [`providers/`](providers) | Which model runs each agent: Claude, Bedrock, OpenAI, Ollama, or GitHub Copilot. |
| [`visuals/`](visuals) | Provided images and clips, Playwright screenshots, login, image generation and the per-scene resolver. |
| [`audio/`](audio) | TTS, the music and sound-effect libraries and the ffmpeg mixer. |
| [`render/`](render) | The bridge that runs the Node renderer and streams its progress, the frame stills, and the subtitle files. |
| [`publish/`](publish) | Publishing to YouTube, LinkedIn, TikTok and Instagram: accounts, sign-in and one adapter per platform. |

## How a run flows

```
cli.py ───────────────────────────────┐
server/app.py ─► core/workspace.py ───┴─► core/service.py ─┬─► graphs/draft.py       brief ─► script
                                                           └─► graphs/production.py  scenes, visuals, narrate, music ─► timing
                                                                                     ─► critic ─► [fix ─► recheck] ─► render ─► review ─► sound ─► master
                                                           └─► graphs/publish.py     ready ─► publish (copy) │ approval │ ready ─► post_<platform> ×4
every node ─► core/events.py ─► terminal, UI (server-sent events), run.log.jsonl
```

## Extending

- **New CLI command:** add a function to `cli.py` that loads inputs and calls one `Service` method. Put the behaviour in `core/service.py` so the M3 UI gets it too.
- **New graph step:** see [`nodes/README.md`](nodes/README.md) (deterministic) or [`agents/README.md`](agents/README.md) (LLM).
- **New config option:** add it to `Config` in `config.py` (unknown keys are rejected) and to [`config.example.yaml`](../../config.example.yaml).

## Rules

- Graph code never knows which provider is in use; only `providers/` does.
- Deterministic work never goes through an LLM, and LLM output is always a validated Pydantic model.
- Anything that can block (TTS, Playwright, ffmpeg) runs in a worker thread so parallel branches really overlap.

See also: [docs/architecture.md](../../docs/architecture.md).
