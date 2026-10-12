from __future__ import annotations

from reelhive.agents.critic import scenes_block, voice_wpm
from reelhive.agents.plan import ScenePlan, brief_block, intro_position, keep_direction, notes_block, research_block
from reelhive.core.context import RunContext
from reelhive.nodes.base import AgentNode
from reelhive.nodes.timing_node import (
    LEAD,
    available_seconds,
    holds,
    intro_seconds,
    place_urls,
    tail_for,
    target_words,
)
from reelhive.schemas.scene_spec import Intro


def fit_words(ctx: RunContext) -> int:
    """Words that fit the target at the voice's measured rate, leaving each scene its minimum padding."""
    assert ctx.spec
    if not ctx.narrated:
        return target_words(ctx.brief)
    padding = len(ctx.spec.scenes) * (LEAD + tail_for(ctx.brief)) + sum(holds(ctx.spec).values())
    speech = available_seconds(ctx.brief, intro_seconds(ctx.spec)) - padding
    return max(10, round(min(speech * voice_wpm(ctx.spec, ctx.narrated) / 60, target_words(ctx.brief) * 1.15)))


class FixerNode(AgentNode):
    name = "fix"
    tier = "strong"
    prompt = "fixer"
    output = ScenePlan

    def build_prompt(self, ctx: RunContext) -> str:
        assert ctx.spec
        failures = "\n".join(f"- {f}" for f in ctx.failures)
        return (
            f"{brief_block(ctx.brief)}\n\n"
            f"Target: about {fit_words(ctx)} narration words in total "
            f"(this voice speaks about {round(voice_wpm(ctx.spec, ctx.narrated))} words per minute).\n"
            f"Idea for the closing call to action: {ctx.brief.closing}\n"
            f"{notes_block(ctx.brief)}{research_block(ctx)}\n\n"
            f"Current scenes:\n{scenes_block(ctx.spec, ctx.narrated)}\n\nFailures:\n{failures}"
        )

    def apply(self, ctx: RunContext, out: ScenePlan) -> None:
        assert ctx.spec
        shown = {"template", "text", "narration", "covers", "layout", "hold", "visual_request"}
        before = {s.index: s.model_dump(include=shown) for s in ctx.spec.scenes}
        previous = {s.index: s for s in ctx.spec.scenes}
        old = {s.index: s.narration for s in ctx.spec.scenes}
        ctx.spec.scenes = [p.to_scene(i, p.narration or old.get(i, "")) for i, p in enumerate(out.scenes, start=1)]
        if out.intro and not ctx.brief.intro:  # the brief's own intro text is never rewritten
            ctx.spec.intro = Intro(**out.intro.model_dump())
        place_urls(ctx.spec, ctx.brief)
        ctx.spec.intro_at = intro_position(ctx.spec.scenes)
        for scene in ctx.spec.scenes:
            prior = previous.get(scene.index)
            keep_direction(out.scenes[scene.index - 1], scene, prior)
            if prior:
                scene.voice_override, scene.duration_override = prior.voice_override, prior.duration_override
            if prior and scene.visual_request == prior.visual_request:
                scene.visual = prior.visual
                scene.image_approved = prior.image_approved
        after = {s.index: s.model_dump(include=shown) for s in ctx.spec.scenes}
        changes = [
            {"scene": i, "before": before.get(i), "after": after.get(i)}
            for i in sorted(before.keys() | after.keys())
            if before.get(i) != after.get(i)
        ]
        ctx.events.emit("fix.diff", node=self.name, changes=changes)
        ctx.events.emit("node.task", node=self.name, task=f"{len(changes)} scenes changed")
