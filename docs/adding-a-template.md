# Adding a template

A template is a pair: a Pydantic model that says what text it takes, and a Revideo component that draws it. The contract between them is generated, so the order matters.

## 1. Define the text and scene in Python

In `src/reelhive/schemas/scene_spec.py`, add the text model with `max_length` on every field, a scene class with a `template` literal, and add both to the `Scene` union and `TEMPLATES`:

```python
class QuoteText(BaseModel):
    quote: str = Field(max_length=120)
    author: str | None = Field(None, max_length=40)


class QuoteScene(_SceneBase):
    template: Literal["quote"] = "quote"
    text: QuoteText
```

## 2. Teach the planner about it

In `src/reelhive/agents/plan.py`, add it to `TEXT_MODELS` and `SCENE_MODELS`, add the literal to `PlannedScene.template`, and map the planner's `headline` / `secondary` fields onto your text model in `PlannedScene.text()`. Then describe when to use it in `src/reelhive/agents/prompts/scene_planner.md`. That is a prompt change, so the eval gate will run on your PR.

## 3. Export the contract

```bash
make schema    # writes renderer/src/spec.schema.json
```

## 4. Draw it

Add `renderer/src/templates/quote.tsx` exporting a generator `function* quote(view, scene)`. Size everything from `view.width()` / `view.height()` so that 16:9, 9:16 and 1:1 all work, take colors from `currentTheme()`, and finish with `yield* playFor(view, node, scene.duration)` so that the scene takes exactly its duration. Register it in `renderer/src/templates/index.ts`. The `Template` type in `renderer/src/spec.ts` and the `TEXT_DEFS` map there need the new name too.

## 5. Check it

```bash
make test        # contract test + vitest: every schema template has a component, limits are read from the schema
make test-slow   # optional: a real render
```

Then render one by hand at all three formats and look at it. A template nobody has looked at in 9:16 is not done.
