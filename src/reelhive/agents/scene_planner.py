from __future__ import annotations

import asyncio
import json

from strands.types.event_loop import Usage

from reelhive.agents.plan import ScenePlan, brief_block
from reelhive.core.context import RunContext
from reelhive.nodes.base import AgentNode
from reelhive.schemas.scene_spec import FORMATS, SceneSpec
from reelhive.visuals.resolver import catalog, theme_for


class ScenePlannerNode(AgentNode):
    name = "scenes"
    tier = "fast"
    prompt = "scene_planner"
    output = ScenePlan

    async def execute(self, ctx: RunContext) -> Usage:
        ctx.visual_catalog = await asyncio.to_thread(catalog, ctx)
        if ctx.brief.level == "high" and ctx.brief.scenes:
            from reelhive.schemas.scene_spec import FORMATS, SceneSpec

            width, height = FORMATS[ctx.brief.format]
            ctx.spec = SceneSpec(
                format=ctx.brief.format,
                width=width,
                height=height,
                scenes=[s.model_copy(deep=True) for s in ctx.brief.scenes],
                theme=theme_for(ctx),
                music_volume=ctx.brief.music_volume,
            )
            return {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0}
        if ctx.brief.visuals.images and getattr(ctx.brief.visuals.images, "describe_images", False):
            from reelhive.visuals.provided import describe

            await describe(ctx)
        return await super().execute(ctx)

    def build_prompt(self, ctx: RunContext) -> str:
        assert ctx.script
        beats = "\n".join(
            f"{i}. [{b.role}] {b.narration}" + (f" (feature: {b.feature})" if b.feature else "")
            for i, b in enumerate(ctx.script.beats, start=1)
        )
        entries = [{k: v for k, v in entry.items() if k != "file"} for entry in ctx.visual_catalog]
        return (
            f"{brief_block(ctx.brief)}\n\nBeats ({len(ctx.script.beats)}):\n{beats}"
            f"\nVisual catalog: {json.dumps(entries)}"
        )

    def apply(self, ctx: RunContext, out: ScenePlan) -> None:
        assert ctx.script
        beats = ctx.script.beats
        if len(out.scenes) != len(beats):
            raise ValueError(f"scene planner returned {len(out.scenes)} scenes for {len(beats)} beats")
        width, height = FORMATS[ctx.brief.format]
        ctx.spec = SceneSpec(
            theme=theme_for(ctx),
            music_volume=ctx.brief.music_volume,
            format=ctx.brief.format,
            width=width,
            height=height,
            scenes=[p.to_scene(i, b.narration) for i, (p, b) in enumerate(zip(out.scenes, beats, strict=True), 1)],
        )
        ctx.events.emit("node.task", node=self.name, task=f"{len(out.scenes)} scenes planned")
