from __future__ import annotations

from reelhive.agents.plan import ScenePlan, brief_block
from reelhive.core.context import RunContext
from reelhive.nodes.base import AgentNode
from reelhive.schemas.scene_spec import FORMATS, SceneSpec


class ScenePlannerNode(AgentNode):
    name = "scenes"
    tier = "fast"
    prompt = "scene_planner"
    output = ScenePlan

    def build_prompt(self, ctx: RunContext) -> str:
        assert ctx.script
        beats = "\n".join(
            f"{i}. [{b.role}] {b.narration}" + (f" (feature: {b.feature})" if b.feature else "")
            for i, b in enumerate(ctx.script.beats, start=1)
        )
        return f"{brief_block(ctx.brief)}\n\nBeats ({len(ctx.script.beats)}):\n{beats}"

    def apply(self, ctx: RunContext, out: ScenePlan) -> None:
        assert ctx.script
        beats = ctx.script.beats
        if len(out.scenes) != len(beats):
            raise ValueError(f"scene planner returned {len(out.scenes)} scenes for {len(beats)} beats")
        width, height = FORMATS[ctx.brief.format]
        ctx.spec = SceneSpec(
            format=ctx.brief.format,
            width=width,
            height=height,
            scenes=[p.to_scene(i, b.narration) for i, (p, b) in enumerate(zip(out.scenes, beats, strict=True), 1)],
        )
        ctx.events.emit("node.task", node=self.name, task=f"{len(out.scenes)} scenes planned")
