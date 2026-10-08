# `agents/prompts`

**Overview.** The system prompts, one Markdown file per agent, loaded by name with `load_prompt("<name>")`. They are versioned with the code because a prompt is behaviour: changing one changes the videos.

## What's here

| File | Used by |
| --- | --- |
| [`script_writer.md`](script_writer.md) | `script`: beats, roles, verbatim closing, word target |
| [`scene_planner.md`](scene_planner.md) | `scenes`: template choice, on-screen text, visual requests |
| [`music_director.md`](music_director.md) | `music`: mood and tempo |
| [`critic.md`](critic.md) | `critic`: the 1-5 rubric review after the hard checks pass |
| [`fixer.md`](fixer.md) | `fix`, and the extra repair turn for invalid structured output |
| [`suggester.md`](suggester.md) | `suggest` (M6): quick-action buttons |

The per-run facts (brief, beats, limits, target word count, failures) are added by each agent's `build_prompt`; these files hold the stable instructions.

## Changing a prompt

1. Edit the file. Keep instructions concrete and say how to use the output tool.
2. Run the core eval against the baseline:
   `uv run reelhive eval --providers claude --set core --baseline evals/baselines/claude-core.json`
3. A drop of more than 5% on any gated metric fails. If the trade-off is intended, refresh the baseline in the same PR (`make eval-baseline`) and explain why.

CI runs the same gate (`.github/workflows/eval-gate.yml`) on every PR that touches this folder.
