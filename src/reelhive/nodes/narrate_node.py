from __future__ import annotations

from reelhive.core.context import RunContext
from reelhive.nodes.base import FunctionNode


def narrate(ctx: RunContext, index: int, text: str) -> float:
    """Speak one scene's narration to audio/scene_XX.wav and record its real length."""
    voice = ctx.brief.voice
    seconds = ctx.tts.synth(text, ctx.path("audio", f"scene_{index:02d}.wav"), voice.gender, voice.accent, voice.speed)
    ctx.narrated[index] = (text, seconds)
    return seconds


class NarrateNode(FunctionNode):
    """Run TTS for every beat (scene N speaks beat N)."""

    name = "narrate"

    def run(self, ctx: RunContext) -> None:
        assert ctx.script
        beats = ctx.script.beats
        for i, beat in enumerate(beats, start=1):
            ctx.events.emit(
                "node.task", node=self.name, task=f"Voicing beat {i} of {len(beats)}", done=i - 1, total=len(beats)
            )
            narrate(ctx, i, beat.narration)
