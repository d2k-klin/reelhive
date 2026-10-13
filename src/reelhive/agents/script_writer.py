from __future__ import annotations

from pydantic import Field, model_validator
from strands.types.event_loop import Usage

from reelhive.agents.plan import brief_block, notes_block, research_block
from reelhive.core.context import RunContext
from reelhive.nodes.base import AgentNode
from reelhive.nodes.timing_node import SHOT, beats_for, max_beat_words, target_words
from reelhive.schemas.script import Beat, Script

BEAT_SLACK = 2  # the writer may use a couple of beats more or fewer than the target, where the story needs it


def script_model(beats: int, max_words: int) -> type[Script]:
    """`Script` with the beat count this video needs, each beat short enough for one shot: the count sets how often
    the screen changes, the cap how long any one screen stays. Out of range goes back to the model as a validation
    error."""
    low, high = max(2, beats - BEAT_SLACK), beats + BEAT_SLACK

    class Sized(Script):
        beats: list[Beat] = Field(min_length=low, max_length=high, description=f"{low}-{high} beats, one per shot")

        @model_validator(mode="after")
        def short_beats(self) -> Sized:
            long = [
                f"beat {i}: {n} words"
                for i, b in enumerate(self.beats, 1)
                if (n := len(b.narration.split())) > max_words
            ]
            if long:
                raise ValueError(f"each beat is one shot of at most {max_words} words; split these: {long}")
            return self

    Sized.__name__ = Sized.__qualname__ = "Script"
    return Sized


class ScriptWriterNode(AgentNode):
    name = "script"
    tier = "strong"
    prompt = "script_writer"
    output = Script

    async def execute(self, ctx: RunContext) -> Usage:
        self.output = script_model(beats_for(ctx.brief), max_beat_words(ctx.brief))
        return await super().execute(ctx)

    def build_prompt(self, ctx: RunContext) -> str:
        beats = beats_for(ctx.brief)
        return (
            f"{brief_block(ctx.brief)}\n\n{notes_block(ctx.brief)}{research_block(ctx)}\n\n"
            f"Target: about {target_words(ctx.brief)} words in total across all beats.\n"
            f"Beats: about {beats} ({max(2, beats - BEAT_SLACK)}-{beats + BEAT_SLACK}), so each shot stays on screen "
            f"about {SHOT[ctx.brief.pacing][0]:g} seconds: one short idea per beat, one or two short sentences, "
            f"at most {max_beat_words(ctx.brief)} words (names and numbers take longer to say).\n"
            f"Idea for the closing call to action (polish it, don't copy it): {ctx.brief.closing}\n"
            f"Editing note: {ctx.note}"
        )

    def apply(self, ctx: RunContext, out: Script) -> None:
        script = Script.model_validate(out.model_dump())
        ctx.script = script
        ctx.path("script.json").write_text(script.model_dump_json(indent=2))
        ctx.events.emit("node.task", node=self.name, task=f"{len(script.beats)} beats written")
