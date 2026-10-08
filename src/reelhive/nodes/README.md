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
| [`render_node.py`](render_node.py) | `render`: writes `spec.json`, runs the renderer, mixes and muxes `video.mp4` (stops after `spec.json` in eval mode). |

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

`WPM_TARGET` (145) is what the script aims for, `SPEECH_WPM` (161) is Kokoro's measured rate, and `LEAD` / `TAIL` / `TAIL_MIN` / `MAX_EXTRA` shape the padding. Changing them changes every video's length. Run the evals before and after (`reelhive eval`).
