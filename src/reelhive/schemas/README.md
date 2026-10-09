# `schemas`

**Overview.** The Pydantic models that define ReelHive's data: what the user asks for, what the script is, and what the renderer draws. They validate every boundary (user YAML, LLM output, the Python→Node handoff), so bad data fails early with a clear message.

## What's here

| File | Model | Notes |
| --- | --- | --- |
| [`brief.py`](brief.py) | `Brief`, `Voice`, `Brand`, `Visuals` (`Screenshots`, `Images`, `Generate`) | User input. `extra="forbid"`: a typo is an error. Shortcuts like `visuals: {url: ...}` expand here. |
| [`script.py`](script.py) | `Script`, `Beat` (each beat lists the key-point notes it tells in `covers`) | The draft graph's output; what a medium or high user edits before `approve`. |
| [`voice.py`](voice.py) | `Voice` | Gender, accent, speed; shared by the brief and per-scene `voice_override`. |
| [`scene_spec.py`](scene_spec.py) | `SceneSpec`, one scene class per template (8), `Theme`, `Credit`, `VisualRequest`, `VisualAsset` | **The render contract.** At `high` the brief carries a list of these scenes directly, with `duration_override`, `voice_override` and `image_approved`. Character limits live here as `max_length`. `FORMATS`, `CREDIT_TEXT` and `TEMPLATES` too. |

## The render contract

`scene_spec.py` is exported to `renderer/src/spec.schema.json` by `make schema` (`python -m reelhive.schemas.scene_spec`). The renderer reads limits from that file, and `tests/unit/test_contract.py` fails if the committed schema and the models drift apart. **After any change here, run `make schema` and commit the JSON.**

## Extending

- **New brief field:** add it to `Brief` with a default, use it in the right agent's `build_prompt` or node, and document it in [docs/brief-reference.md](../../../docs/brief-reference.md).
- **New template:** follow [docs/adding-a-template.md](../../../docs/adding-a-template.md); it starts here.
- **New level:** the `level` literal is here; the defaults and stops live in [`../levels.py`](../levels.py).
