"""M6 quick actions (plan §3.10): 3-4 suggestions for one beat or scene, shown as buttons.

Not a graph node: it runs on demand during the approval stops. It never edits the run;
applying a suggestion goes through the regenerate path with the instruction as the note.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from strands import Agent
from strands.models.model import Model

from reelhive.agents.plan import brief_block
from reelhive.core.events import EventBus
from reelhive.nodes.base import load_prompt
from reelhive.schemas.brief import Brief
from reelhive.schemas.scene_spec import SceneSpec
from reelhive.schemas.script import Script

Target = Literal["beat", "scene"]


class Suggestion(BaseModel):
    label: str = Field(min_length=2, max_length=28, description="Button text, 2-4 words")
    instruction: str = Field(min_length=10, max_length=240, description="The note the regenerating agent receives")


class Suggestions(BaseModel):
    suggestions: list[Suggestion] = Field(min_length=3, max_length=4)

    @field_validator("suggestions")
    @classmethod
    def _distinct(cls, value: list[Suggestion]) -> list[Suggestion]:
        if len({s.label.lower() for s in value}) != len(value):
            raise ValueError("labels must be distinct")
        return value


def target_json(kind: Target, index: int, script: Script, spec: SceneSpec | None) -> str:
    """The exact beat or scene being suggested for; its hash is the cache key (one entry per version)."""
    if kind == "beat":
        if not 1 <= index <= len(script.beats):
            raise ValueError(f"beat {index} does not exist (1-{len(script.beats)})")
        return script.beats[index - 1].model_dump_json()
    if spec is None:
        raise ValueError("this run has no scene spec yet; suggest for a beat instead")
    scene = next((s for s in spec.scenes if s.index == index), None)
    if scene is None:
        raise ValueError(f"scene {index} does not exist (1-{len(spec.scenes)})")
    return scene.model_dump_json(include={"template", "text", "narration", "feature", "duration", "visual_request"})


def build_prompt(kind: Target, index: int, brief: Brief, script: Script, current: str) -> str:
    beats = "\n".join(f"{i}. [{b.role}] {b.narration}" for i, b in enumerate(script.beats, start=1))
    return (
        f"{brief_block(brief)}\n\nWhole script for context:\n{beats}\n\n"
        f"Suggest edits for {kind} {index} only:\n{current}"
    )


async def suggest(
    model: Model,
    run_dir: Path,
    kind: Target,
    index: int,
    brief: Brief,
    script: Script,
    spec: SceneSpec | None = None,
    events: EventBus | None = None,
    fresh: bool = False,
) -> Suggestions:
    current = target_json(kind, index, script, spec)
    key = hashlib.sha256(current.encode()).hexdigest()[:16]
    cache = run_dir / "suggestions" / f"{kind}_{index:02d}_{key}.json"
    cached = cache.exists() and not fresh  # "More ideas" asks for a fresh set
    if cached:
        result = Suggestions.model_validate_json(cache.read_text())
        tokens = 0
    else:
        agent = Agent(model=model, system_prompt=load_prompt("suggester"), callback_handler=None)
        out = await agent.invoke_async(
            build_prompt(kind, index, brief, script, current), structured_output_model=Suggestions
        )
        result = Suggestions.model_validate(out.structured_output)
        tokens = out.metrics.accumulated_usage["totalTokens"]
        cache.parent.mkdir(exist_ok=True)
        cache.write_text(result.model_dump_json(indent=2))
    if events:
        events.emit(
            "suggestion.offered",
            target=kind,
            index=index,
            version=key,
            cached=cached,
            tokens=tokens,
            suggestions=json.loads(result.model_dump_json())["suggestions"],
        )
    return result
