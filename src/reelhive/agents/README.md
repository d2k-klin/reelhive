# `agents`

**Overview.** The LLM side of ReelHive. Each graph agent is an `AgentNode` with a system prompt, a Pydantic output model, a `build_prompt` (what it sees) and an `apply` (what it changes in the run). `suggest` is the one agent that is not a graph node: it runs on demand while a run is paused.

## What's here

| File | Agent | Tier | Output |
| --- | --- | --- | --- |
| [`researcher.py`](researcher.py) | `research`: reads the product website (via the screenshot crawler, text only) and writes product notes | fast | `ProductNotes` |
| [`script_writer.py`](script_writer.py) | `script`: narration as beats, sized to the target word count | strong | `Script` |
| [`scene_planner.py`](scene_planner.py) | `scenes`: template, on-screen text and visual request per beat; builds the `SceneSpec` and theme. At `high`, the brief's own scenes are used as is (no LLM call). | fast | `ScenePlan` |
| [`music_director.py`](music_director.py) | `music`: mood and BPM, then a library track | fast | `MusicChoice` |
| [`critic.py`](critic.py) | `critic`: the hard checks (`hard_checks`, `run_gates`: duration, closing, features, pace, text limits, audio, images, product UI, voice fit, and image approval at `high`), then a rubric `Verdict` only if they pass | strong | `Verdict` |
| [`fixer.py`](fixer.py) | `fix`: a corrected `ScenePlan` with narration; emits `fix.diff` | strong | `ScenePlan` |
| [`plan.py`](plan.py) | `PlannedScene` / `ScenePlan`, shared by planner and fixer; enforces template character limits so the model retries rather than us truncating | – | – |
| [`suggester.py`](suggester.py) | `suggest` (M6): 3-4 quick-action suggestions for one beat or scene, cached per version | fast | `Suggestions` |
| [`prompts/`](prompts) | The system prompts, one Markdown file per agent | – | – |

## Extending: a new agent node

1. Add the prompt as `prompts/<name>.md`.
2. Subclass `AgentNode` with `name`, `tier`, `prompt`, `output`, `build_prompt(ctx)` and `apply(ctx, out)`. Put validation in the output model, so invalid output goes back to the model.
3. Add the node name to the `nodes:` literal in `config.py` and to `NODE_TIERS` in `providers/factory.py`, so it can be overridden per provider.
4. Wire it into a graph and test it with `FakeModel` (canned output keyed by the output model's class name).

## Rules

- Agents never write renderer code or files outside their `apply`; they fill typed models.
- Never hardcode model names; tiers map to models in `config.yaml`.
- A prompt change can make videos worse. Run `reelhive eval` against the baseline before merging (CI's eval gate does this on PRs).
