# `nodes`

**Overview.** Graph nodes that do deterministic work (no LLM), plus the two base classes every ReelHive node uses. Each node is a Strands `MultiAgentBase`, reads and writes the shared `RunContext`, and emits the same events.

## What's here

| File | Node / purpose |
| --- | --- |
| [`base.py`](base.py) | `FunctionNode` (override `run(ctx)`, which runs in a worker thread; emits `node.started` / `node.finished`) and `AgentNode` (builds a prompt, calls a Strands `Agent` with structured output, gets one repair turn on invalid output, applies the result; hands off to Copilot when configured). `load_prompt()` reads `agents/prompts/*.md`. |
| [`brief_node.py`](brief_node.py) | `brief`: fills level defaults, makes paths absolute, writes `brief.yaml`. |
| [`narrate_node.py`](narrate_node.py) | `narrate`: TTS per beat to `audio/scene_XX.wav`; `narrate()` is reused by `recheck`. |
| [`visuals_node.py`](visuals_node.py) | `visuals`: calls `visuals/resolver.resolve`. |
| [`timing_node.py`](timing_node.py) | `timing`: scene starts and lengths from real speech plus padding, landing on the target; also the credit rule, `target_words()` and the speech-rate constants. |
| [`recheck_node.py`](recheck_node.py) | `recheck`: after `fix`, re-voice changed scenes, re-resolve visuals, re-time, run the hard checks again. |
| [`render_node.py`](render_node.py) | `render`: writes `spec.json` and runs the renderer, which draws `render/silent.mp4` and reports the measured layout in `render/layout.json` (stops after `spec.json` in eval mode). A new cut reopens `review`, `sound` and `master`. |
| [`master_node.py`](master_node.py) | `master`: mixes narration, ducked music and any sound effects, muxes them onto the reviewed cut as `video.mp4`, and writes the subtitles (`video.srt`, `video.vtt` and a soft track) when there is narration. |
| [`publish_nodes.py`](publish_nodes.py) | Publishing: `ready` (gates per platform before any model call or upload: the finished video, the developer app's credentials, a signed-in account, the platform's length and size rules) and `post_youtube`, `post_linkedin`, `post_tiktok`, `post_instagram`, which run in parallel and record each result as it lands. |

## Extending: a new deterministic node

```python
class WatermarkNode(FunctionNode):
    name = "watermark"

    def run(self, ctx: RunContext) -> None:
        ctx.events.emit("node.task", node=self.name, task="Stamping frames")
        ...  # read/write ctx fields; write files with ctx.path(...)
```

Then wire it in [`../graphs/production.py`](../graphs/production.py). Emit `node.task` for anything slow so the CLI and UI show progress. Raise on failure; the base class reports it and the run fails cleanly.

## Timing constants

`PACE` holds each brief `pacing`'s narration range and target (balanced aims for 145), `SHOT` its average and longest shot (`beats_for()` turns the average into the script's beat count), `FINAL_HOLD` lets the closing frame settle, `SPEECH_WPM` (145) is Kokoro's measured rate on real scripts, and `LEAD` / `TAILS` (the pause after each beat, by pacing) / `TAIL_MIN` / `MAX_EXTRA` shape the padding. Changing them changes every video's length. Run the evals before and after (`reelhive eval`).
