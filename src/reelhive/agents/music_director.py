from __future__ import annotations

from pydantic import BaseModel, Field
from strands.types.event_loop import Usage

from reelhive.agents.plan import brief_block
from reelhive.audio.music_library import MOODS, pick_track
from reelhive.core.context import RunContext
from reelhive.nodes.base import AgentNode, _no_usage


class MusicChoice(BaseModel):
    mood: str = Field(description=f"One of: {', '.join(MOODS)}")
    bpm: int = Field(ge=60, le=160)
    reason: str


class MusicDirectorNode(AgentNode):
    name = "music"
    tier = "fast"
    prompt = "music_director"
    output = MusicChoice

    async def execute(self, ctx: RunContext) -> Usage:
        if not ctx.brief.music:  # no track wanted: skip the model call
            ctx.events.emit("node.task", node=self.name, task="Music turned off in the brief")
            return _no_usage()
        return await super().execute(ctx)

    def build_prompt(self, ctx: RunContext) -> str:
        return f"{brief_block(ctx.brief)}\n\nAllowed moods: {', '.join(MOODS)}"

    def apply(self, ctx: RunContext, out: MusicChoice) -> None:
        if ctx.brief.music_track:
            from reelhive.audio.music_library import MUSIC_DIR, load_manifest

            track = next((t for t in load_manifest() if t["file"] == ctx.brief.music_track), None)
            if not track:
                raise ValueError("music_track must name a track in the CC0 library")
            ctx.music = {**track, "file": str(MUSIC_DIR / track["file"])}
            return
        ctx.music = pick_track(ctx.brief.music_mood or out.mood, out.bpm)
        ctx.events.emit("node.task", node=self.name, task=f"{out.mood} at {out.bpm} BPM: {ctx.music['title']}")
