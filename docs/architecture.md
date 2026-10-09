# Architecture

ReelHive turns a brief into a video in two Strands graphs, driven by one core service that the CLI (and, from M3, the local UI) sit on top of.

```
CLI (cli.py) ─────────────────────────────┐
UI (React) ─► server/ ─► core/workspace.py ┴─► core/service.py ─► draft graph ─(stop: medium, high)─► production graph ─(stop: high)─► finish          │
                          └──► core/events.py ──► CLI progress · UI stream · run.log.jsonl
```

## The two graphs

A Strands graph runs to completion, so human approval points sit between graph runs.

```
draft:        brief ─► script

production:   ┌─► scenes ─► visuals ─┐
              ├─► narrate ───────────┼─► timing ─► critic ─┬─(pass)─────────────────────► render
              └─► music ─────────────┘                     └─(fail)─► fix ─► recheck ─(pass)─┘
```

| Node | Kind | Job | Code |
| --- | --- | --- | --- |
| `brief` | deterministic | Validate, fill the level's defaults, make paths absolute, save `brief.yaml` | `nodes/brief_node.py` |
| `script` | agent, strong | Narration as beats, sized to the target duration | `agents/script_writer.py` |
| `scenes` | agent, fast | A template, on-screen text and a visual request per beat | `agents/scene_planner.py` |
| `visuals` | deterministic | Resolve each visual request: provided image, screenshot or generated image, else a text fallback | `visuals/resolver.py` |
| `narrate` | deterministic | Kokoro TTS per beat, recording real durations | `nodes/narrate_node.py` |
| `music` | agent, fast + lookup | Mood and BPM, then the closest track in `assets/music` | `agents/music_director.py` |
| `timing` | deterministic | Scene starts and lengths from real audio, padded to the target | `nodes/timing_node.py` |
| `critic` | hard checks + agent | Deterministic gates first; only if they pass, a rubric review | `agents/critic.py` |
| `fix` | agent, strong | Repair the scene plan against the failures | `agents/fixer.py` |
| `recheck` | deterministic | Re-voice changed scenes, re-resolve visuals, re-time, run the gates again | `nodes/recheck_node.py` |
| `render` | deterministic | Revideo renders silent frames; ffmpeg mixes, ducks and muxes | `nodes/render_node.py`, `render/bridge.py`, `audio/mixer.py` |

Deterministic nodes never call an LLM. Agent nodes return Pydantic-validated structured output; the image prompts are written by `scenes`, and `visuals` only executes them.

## Hard checks

`critic` runs these before it spends a token, and `recheck` runs them again after `fix`:

- total duration within ±5% of the target;
- the closing message verbatim in the final scene's narration or on screen;
- every feature covered by a scene;
- narration pace of 130-170 words per minute of video;
- on-screen text within each template's limits;
- every scene voiced with its current narration;
- every image present, inside the run folder and at the format's minimum resolution;
- no generated image in a `product_ui` scene.

If `recheck` still fails, no edge is satisfied, the graph ends, and the service stops the run with the failure report instead of rendering a bad video.

## The render contract

`schemas/scene_spec.py` is the contract between Python and the Node renderer. Pydantic exports it to `renderer/src/spec.schema.json` (`make schema`), and the renderer reads its character limits from that file, so there is one source of truth. A contract test fails if the two drift. Agents never write renderer code; they fill this spec.

## Run folder

Every run is written to disk, which makes it reproducible and resumable:

```
runs/2026-10-08T15-30-00-123456_cloud-bills-grow-silently/
├── brief.yaml        # normalized brief
├── config.json       # provider config, so `approve` resumes on the same models
├── status.json       # queued | drafting | awaiting_script | producing | awaiting_scenes | done | stopped | failed | cancelled | interrupted
├── checkpoint.json   # completed nodes and state, so `reelhive resume` continues after a crash or cancel
├── script.json       # the script (edit it before `reelhive approve` at medium)
├── spec.json         # the final scene spec
├── visuals/          # copied, captured or generated images
├── audio/            # scene_XX.wav, narration.wav, mix.wav
├── render/silent.mp4
├── video.mp4
└── run.log.jsonl     # every event
```

## Events

`core/events.py` defines one stream. The CLI prints it, the UI (M3) will receive it over server-sent events, and every event lands in `run.log.jsonl`, so past runs can be replayed.

| Event | Carries |
| --- | --- |
| `node.started` / `node.finished` / `node.skipped` | node, status, seconds, tokens |
| `node.task` | one human-readable progress line, optionally `progress` 0-1 |
| `agent.text` | streamed model text |
| `gate.result` | check, value, threshold, passed |
| `critic.verdict` | rubric scores, passed, reasons |
| `fix.diff` | before/after of each changed scene |
| `run.paused` / `script.approved` | approval stop and resume |
| `suggestion.offered` / `suggestion.applied` / `version.restored` | M6 quick actions: what was offered (cached or not), which was applied, and undo |
| `run.finished` | video path and duration, or the stop report |

## Providers

`providers/factory.py` turns `config.yaml` into a Strands model per tier (strong: script, critic, fix; fast: scenes, music), with optional per-node overrides. GitHub Copilot is not a Strands model: `AgentNode` hands its work to `CopilotAgentNode`, which runs a locked-down Copilot SDK session with a single submit tool. See [providers.md](providers.md) and [copilot-sdk.md](copilot-sdk.md).

## Evals

`evals/` runs the same graphs in spec-only mode to score scripts, specs and image prompts per provider. See [evals/README.md](../evals/README.md).
