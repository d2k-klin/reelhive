from __future__ import annotations

import asyncio
import json

from strands.types.event_loop import Usage

from reelhive.agents.plan import (
    ScenePlan,
    brief_block,
    intro_position,
    notes_block,
    reading_budget,
    research_block,
    scene_plan_model,
)
from reelhive.core.context import RunContext
from reelhive.nodes.base import AgentNode
from reelhive.nodes.timing_node import SPEECH_WPM, place_urls
from reelhive.schemas.scene_spec import FORMATS, Intro, IntroText, SceneSpec
from reelhive.visuals.resolver import catalog, theme_for


def opening_for(ctx: RunContext, planned: IntroText | None) -> Intro | None:
    """The intro: the brief's own text if it gave one, else the agent's."""
    text = ctx.brief.intro or planned
    return Intro(**text.model_dump()) if text else None


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
                intro=opening_for(ctx, None),
                intro_at=intro_position(ctx.brief.scenes, ctx.brief.cold_open),
                scenes=[s.model_copy(deep=True) for s in ctx.brief.scenes],
                theme=theme_for(ctx),
                music_volume=ctx.brief.music_volume,
            )
            place_urls(ctx.spec, ctx.brief)
            return {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0}
        assert ctx.script
        self.output = scene_plan_model(
            [len(b.narration.split()) for b in ctx.script.beats], SPEECH_WPM * ctx.brief.voice.speed / 60
        )
        if ctx.brief.visuals.images and getattr(ctx.brief.visuals.images, "describe_images", False):
            from reelhive.visuals.provided import describe

            await describe(ctx)
        return await super().execute(ctx)

    def build_prompt(self, ctx: RunContext) -> str:
        assert ctx.script
        rate = SPEECH_WPM * ctx.brief.voice.speed / 60
        beats = "\n".join(
            f"{i}. [{b.role}] {b.narration}"
            + (f" (covers key points {b.covers})" if b.covers else "")
            + f" [at most {reading_budget(len(b.narration.split()), 0.0, rate)} on-screen words]"
            for i, b in enumerate(ctx.script.beats, start=1)
        )
        entries = [{k: v for k, v in entry.items() if k not in ("file", "poster")} for entry in ctx.visual_catalog]
        return (
            f"{brief_block(ctx.brief)}\n\n{notes_block(ctx.brief)}{research_block(ctx)}\n\n"
            f"Beats ({len(ctx.script.beats)}):\n{beats}"
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
            intro=opening_for(ctx, out.intro),
            intro_at=intro_position(out.scenes, ctx.brief.cold_open),
            scenes=[
                p.to_scene(i, b.narration).model_copy(update={"covers": p.covers or b.covers})
                for i, (p, b) in enumerate(zip(out.scenes, beats, strict=True), 1)
            ],
        )
        place_urls(ctx.spec, ctx.brief)
        intro = ctx.spec.intro
        ctx.events.emit("node.task", node=self.name, task=f"Intro: {intro.title}" if intro else "No intro title given")
        ctx.events.emit("node.task", node=self.name, task=f"{len(out.scenes)} scenes planned")
