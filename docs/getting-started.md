# Getting started

Install ReelHive, make a first video from the terminal or the studio, and find every command.

## Install and make your first video

After setup, the [UI user guide](ui-guide.md) and [providers](providers.md) cover the rest.

Requirements: Python 3.11-3.12, Node 20+ and [uv](https://docs.astral.sh/uv/). ffmpeg and espeak-ng are used from your system when installed, and otherwise come bundled with the Python dependencies.

```bash
git clone https://github.com/d2k-klin/reelhive && cd reelhive
make setup                                        # Python + Node deps, browsers for capture and rendering
export ANTHROPIC_API_KEY=...                      # or another AI provider, see providers.md
uv run reelhive doctor                            # checks every dependency and key
uv run reelhive ui                                # the local editing studio, in your browser
# or, without the UI:
uv run reelhive run examples/briefs/low.yaml
```

The video lands in `runs/<timestamp>_<slug>/video.mp4`, next to the script, the scene spec, the audio and a `run.log.jsonl` of every step. Cloning is the install method: the Node renderer lives next to the Python package, so nothing is published to PyPI or npm.

## Customization levels

Low means the agents own more of the work; High means you direct more of it.

| Level | You provide | Stops for approval | Example |
| --- | --- | --- | --- |
| `low` | audience, story, key points, closing idea, duration, format, voice gender; optionally a website or other visual source | none |  [low.yaml](../examples/briefs/low.yaml), [low-screenshots.yaml](../examples/briefs/low-screenshots.yaml) |
| `medium` | + tone, pacing, brand colors and logo, theme, music mood, CTA URL, accent and speed, full `visuals` block | script | [medium.yaml](../examples/briefs/medium.yaml) |
| `high` | + every scene yourself (template, text, narration, duration, voice, image), music track and volume | script, scenes, images | [high.yaml](../examples/briefs/high.yaml), or the studio |

```bash
uv run reelhive run examples/briefs/medium.yaml
# edit runs/<run-folder>/script.json if you like, then:
uv run reelhive approve runs/<run-folder>
```

Every field is in [docs/brief-reference.md](brief-reference.md).

Medium pauses before narration, visual capture/generation and rendering. High pauses again after planning so every scene, voice, duration, visual, and image approval can be edited before rendering. Approval uses the saved provider configuration and never repeats completed nodes. `low` continues automatically. Formats are `16:9` (1920×1080), `9:16` (1080×1920) and `1:1` (1080×1080).

The local studio includes YAML import/export, uploads and test captures, script and scene editors, the same Revideo scene preview used for final output, live graph and gate events, runs history, downloads, resume/cancel controls, and non-secret provider settings. CLI users can edit `spec.json`, run `reelhive regen <run-folder> --scene N`, then `reelhive approve-scenes <run-folder>`.

See the illustrated [UI user guide](ui-guide.md) for launch options and the complete brief-to-download workflow.

## Commands

| Command | What it does |
| --- | --- |
| `reelhive init [folder]` | Write a starter `brief.yaml` and `config.yaml` |
| `reelhive run <brief>` | Make a video (pauses for approval at `medium` and `high`) |
| `reelhive approve <run>` | Continue after reviewing or editing `script.json` |
| `reelhive approve-scenes <run>` | Continue after reviewing the scenes and images (`high`) |
| `reelhive regen <run> --scene N --note "..."` | Redo one scene |
| `reelhive preview <run> --scene N` | Render one scene alone to check it |
| `reelhive resume <run>` | Continue an interrupted or cancelled run from its checkpoint |
| `reelhive ui` | The local editing studio on 127.0.0.1 |
| `reelhive doctor` | Check dependencies, keys and the credit setting |
| `reelhive voices` / `reelhive models` | List voices / available models |
| `reelhive login <url>` / `reelhive capture <brief>` | Save a sign-in for screenshots / preview masked screenshots |
| `reelhive suggest <run> --beat N [--apply K]` | Quick-action suggestions for one beat or scene; apply one |
| `reelhive undo <run> --scene N \| --script` | Restore the previous version after a regeneration |
| `reelhive eval --providers a,b` | Compare providers on the eval set |
