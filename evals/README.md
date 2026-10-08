# Evals

Tests check that the code works. Evals check that the **videos are good**, and let you compare providers.

An eval run sends every brief of a set through the real draft and production graphs, in **spec-only mode**:

- the agents (script, scenes, music, critic, fix) are the real ones, on the provider you choose;
- TTS is a silent stand-in sized to Kokoro's measured rate (161 wpm), so timing and pace are realistic;
- nothing is rendered: the run stops at `spec.json`, the render contract;
- no images are generated: prompts are recorded and judged, and a placeholder takes the image's place;
- screenshot briefs point at a small fixture site (`datasets/site/`) served on 127.0.0.1.

So a full run costs only the LLM calls.

## Running

```bash
uv run reelhive eval --providers claude --set core            # one provider
uv run reelhive eval --providers claude,bedrock,ollama        # comparison (models come from config.yaml)
uv run reelhive eval --providers ollama --judge none          # fully offline, no LLM judge
```

Each run writes `evals/reports/<timestamp>_<set>/` with `report.md`, `report.html` and `results.json` (every run's scores, its run folder, and any error). Reports are gitignored.

| Option | Default | Meaning |
| --- | --- | --- |
| `--providers` | `claude` | Comma-separated providers to compare |
| `--set` | `core` | `core` (all 24 briefs) or `smoke` (5 briefs, used nightly) |
| `--judge` | `claude` | Provider whose strong model judges every provider's output, or `none` |
| `--baseline` | – | Fail (exit 1) on a regression of more than 5% |
| `--save-baseline` | – | Write this run's aggregates as a baseline |
| `--concurrency` | `4` | Briefs evaluated at once |

## Reading a report

One table, one row per metric, one column per provider.

**Deterministic metrics** (no LLM; the critic's hard checks as scores, in `metrics/deterministic.py`):

| Metric | What it means |
| --- | --- |
| Reached render | The run passed the hard checks (directly or after one `fix`) and produced a spec |
| Schema valid on first try | No agent needed the extra repair round for invalid structured output |
| Fix iterations | How often the `fix` path ran (0 or 1 per brief) |
| Duration within ±5%, duration error | Final spec length against the brief's target |
| Closing message exact match | The closing appears verbatim in the final scene |
| Feature coverage | Share of the brief's features covered by a scene |
| Pace 130-170 wpm | Narration density over the video's length |
| No text overflow | Every scene's on-screen text fits its template |
| Visual coverage | Share of scenes that asked for a visual and got one, when the brief has a source |
| Generated images in product UI | Must be 0; generated images never stand in for the user's product |
| Images, tokens, wall time | Per brief, plus seconds and tokens per node |

**Judge metrics** (1-5, fixed rubrics in `rubrics/`): hook, clarity, audience fit, storyline adherence and call to action for the script; relevance, style consistency and "no product UI" for image prompts.

## The prompt-change gate

Any PR that touches `src/reelhive/agents/prompts/`, the rubrics, the dataset or the baseline runs `.github/workflows/eval-gate.yml`: the core set on Claude, compared with `evals/baselines/claude-core.json`. Every gated metric (the higher-is-better rows) may drop by at most 5%, relative; generated product UI must stay at 0.

To create or refresh the baseline after an intended change:

```bash
make eval-baseline        # runs the core set on Claude and writes evals/baselines/claude-core.json
git add evals/baselines/claude-core.json
```

The gate needs the `ANTHROPIC_API_KEY` repository secret. Pull requests from forks don't get secrets, so a maintainer reruns the gate for them.

## Adding briefs

Add a YAML file to `datasets/briefs/` and its name to `datasets/sets.yaml`. Briefs are ordinary ReelHive briefs; `${SITE}` and `${DATASET}` are filled in at run time. Keep the dataset at 20-30 briefs that cover technical and non-technical audiences, 15 s to 3 min, all three formats, 1 to 8 features, tricky closings (URLs, numbers) and every visual source combination. Changing the dataset changes the baseline, so refresh it in the same PR.
