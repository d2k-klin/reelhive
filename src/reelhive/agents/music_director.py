from __future__ import annotations

from pydantic import BaseModel, Field

from reelhive.agents.plan import brief_block
from reelhive.audio.music_library import MOODS, pick_track
from reelhive.core.context import RunContext
from reelhive.nodes.base import AgentNode


class MusicChoice(BaseModel):
    mood: str = Field(description=f"One of: {', '.join(MOODS)}")
    bpm: int = Field(ge=60, le=160)
    reason: str


class MusicDirectorNode(AgentNode):
    name = "music"
    tier = "fast"
    prompt = "music_director"
    output = MusicChoice

    def build_prompt(self, ctx: RunContext) -> str:
        return f"{brief_block(ctx.brief)}\n\nAllowed moods: {', '.join(MOODS)}"

    def apply(self, ctx: RunContext, out: MusicChoice) -> None:
        ctx.music = pick_track(out.mood, out.bpm)
        ctx.events.emit("node.task", node=self.name, task=f"{out.mood} at {out.bpm} BPM: {ctx.music['title']}")
