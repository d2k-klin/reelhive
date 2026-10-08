# `visuals/generators`

**Overview.** Backends that turn a concept prompt into an image file. They are independent of the agent provider: Claude can write the script while OpenAI draws the illustrations.

## What's here

| File | What it is |
| --- | --- |
| [`base.py`](base.py) | `ImageGenerator` protocol: `generate(prompt, size, output) -> dict` (usage and an optional `cost_usd`). |
| [`openai.py`](openai.py) | `OpenAIImageGenerator`: the OpenAI image API, with the model from `config.yaml` `image_generation.model` (never hardcoded) and the cost estimate from `image_generation.cost_per_image`. |

The resolver adds the brief's style and brand colors to every prompt, caches results by prompt, size and model, and counts every attempt (including failures) against `max_images`, so a generator only has to make one image.

## Extending: a new backend (e.g. Bedrock)

1. Add `bedrock.py` with a class implementing `generate`. Write the image bytes to `output` and return a usage dict.
2. Add the backend name to `Generate.provider` in `schemas/brief.py`, and pick the class in `visuals/resolver.py` where `OpenAIImageGenerator` is created.
3. Test it the way `test_openai_generator_writes_bytes_and_usage` does, with the client faked.

Evals and tests never call a real generator: they inject `PromptRecorder` / `FakeImageGenerator` through `RunContext.image_generator`.
