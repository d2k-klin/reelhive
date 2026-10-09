"""LLM-as-judge with fixed rubrics (plan §7). One judge model scores every provider's output."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from strands import Agent
from strands.models.model import Model

from reelhive.schemas.brief import Brief, Generate
from reelhive.schemas.scene_spec import SceneSpec
from reelhive.schemas.script import Script

RUBRICS = Path(__file__).parents[1] / "rubrics"
Score = Field(ge=1, le=5)


class ScriptJudgement(BaseModel):
    hook: int = Score
    clarity: int = Score
    audience_fit: int = Score
    storyline: int = Score
    cta: int = Score
    notes: str = ""


class SuggestionJudgement(BaseModel):
    specific: int = Score
    label_fidelity: int = Score
    variety: int = Score
    safe: int = Score


class PromptScore(BaseModel):
    scene: int
    relevance: int = Score
    style: int = Score
    no_product_ui: int = Score


class PromptJudgement(BaseModel):
    scores: list[PromptScore]


def concept_prompts(spec: SceneSpec) -> list[tuple[int, str, str]]:
    return [
        (s.index, s.visual_request.prompt, s.narration)
        for s in spec.scenes
        if s.visual_request.kind == "concept" and s.visual_request.prompt
    ]


async def _ask(model: Model, rubric: str, prompt: str, output: type[BaseModel]) -> tuple[Any, int]:
    agent = Agent(model=model, system_prompt=(RUBRICS / rubric).read_text(), callback_handler=None)
    result = await agent.invoke_async(prompt, structured_output_model=output)
    return result.structured_output, result.metrics.accumulated_usage["totalTokens"]


async def judge_run(model: Model, brief: Brief, script: Script, spec: SceneSpec | None) -> dict[str, Any]:
    beats = "\n".join(f"{i}. [{b.role}] {b.narration}" for i, b in enumerate(script.beats, 1))
    verdict, tokens = await _ask(
        model,
        "script.md",
        f"Audience: {brief.audience}\nStoryline: {brief.storyline}\nTone: {brief.tone}\n"
        f"Closing message: {brief.closing}\n\nScript:\n{beats}",
        ScriptJudgement,
    )
    scores: dict[str, Any] = {f"judge_{k}": v for k, v in verdict.model_dump(exclude={"notes"}).items()}
    scores["judge_notes"] = verdict.notes
    prompts = concept_prompts(spec) if spec else []
    if prompts:
        style = brief.visuals.generate.style if isinstance(brief.visuals.generate, Generate) else "(none given)"
        listed = "\n".join(f"Scene {i}: prompt: {p}\n  narration: {n}" for i, p, n in prompts)
        judged, more = await _ask(model, "image-prompts.md", f"Requested style: {style}\n\n{listed}", PromptJudgement)
        tokens += more
        for field in ("relevance", "style", "no_product_ui"):
            values = [getattr(s, field) for s in judged.scores]
            scores[f"judge_prompt_{field}"] = sum(values) / len(values) if values else None
    scores["judge_tokens"] = tokens
    return scores


async def judge_suggestions(model: Model, brief: Brief, script: Script, suggestions: Any) -> dict[str, Any]:
    """M6: score the quick actions offered for the first beat (plan §7, suggestions metric)."""
    beats = "\n".join(f"{i}. [{b.role}] {b.narration}" for i, b in enumerate(script.beats, 1))
    listed = "\n".join(f"- {s.label}: {s.instruction}" for s in suggestions.suggestions)
    verdict, tokens = await _ask(
        model,
        "suggestions.md",
        f"Audience: {brief.audience}\nStoryline: {brief.storyline}\nClosing message: {brief.closing}\n\n"
        f"Script:\n{beats}\n\nSuggestions for beat 1:\n{listed}",
        SuggestionJudgement,
    )
    return {**{f"judge_suggestion_{k}": v for k, v in verdict.model_dump().items()}, "judge_tokens_suggestions": tokens}
