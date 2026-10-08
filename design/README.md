# `design`

**Overview.** The source of ReelHive's illustrations: the Mr.D style guide, and the prompts that produce candidate mascot poses, role portraits and illustrated icons. Art is made here at design time and curated by hand. **Nothing is generated while ReelHive runs.**

## What's here

| Path | What it is |
| --- | --- |
| [`style-guide.md`](style-guide.md) | The Mr.D look, palette, do and don't list, and the checklist for committing an asset |
| [`prompts/_style.yaml`](prompts/_style.yaml) | The shared style block, reference image and size added to every prompt |
| [`prompts/mascot.yaml`](prompts/mascot.yaml) | The six new mascot poses (welcome, directing, thinking, celebrating, puzzled, sleeping) |
| [`prompts/roles.yaml`](prompts/roles.yaml) | Mr.D as each of the 12 nodes, including the M6 Editor |
| [`prompts/icons.yaml`](prompts/icons.yaml) | The illustrated icons for levels, sources, formats, moods, providers and empty and error states |
| `candidates/` | Gitignored: raw generations to choose from |

## Making an asset

```bash
uv run python scripts/generate_assets.py --dry-run                 # print every composed prompt, no API call
uv run python scripts/generate_assets.py --only mr-d-thinking      # 4 candidates into design/candidates/mr-d-thinking/
uv run python scripts/generate_assets.py --file roles --count 2    # every role, 2 candidates each
```

Generation uses OpenAI image editing with the reference image (`assets/brand/mr-d-laptop@2x.webp`), so the character stays the same. It needs `OPENAI_API_KEY`, and takes the model from `config.yaml` `image_generation.model` (or `--model`). It costs money per image, so start with `--only` and `--count 1`.

Then:

1. Pick the best candidate by hand against [`style-guide.md`](style-guide.md), and fix details if needed.
2. Export transparent WebP at 1x and 2x (plus a 1024 px master for the archive).
3. **Mascot poses and role portraits** are Mr.D brand work: they go to Dav's brand set (archived in S3) and come back into [`assets/brand/`](../assets/brand) with an updated `manifest.json`. A test checks every file's SHA-256 and the 2 MB budget. **Icons** are ReelHive's own and go to `ui/src/assets/icons/`.

## Extending

Add an entry (`name` and `prompt`) to the right YAML file; the name becomes the folder in `candidates/` and the file name. Describe the prop or object only: the character and style come from `_style.yaml`. `tests/unit/test_design.py` checks that names are unique and that every graph node has a role portrait prompt.

## Status

The UI ships the five supplied illustrations (`assets/brand/`). The six new poses, the 12 role portraits and the icons from these prompts are still to be generated, curated and supplied (UI plan §10).
