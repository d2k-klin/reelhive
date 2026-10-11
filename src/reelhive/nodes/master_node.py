from __future__ import annotations

from reelhive.audio import mixer
from reelhive.core.context import RunContext
from reelhive.nodes.base import FunctionNode


class MasterNode(FunctionNode):
    """Mix narration and music with ffmpeg (ducking the music under the voice) and mux them onto the reviewed cut."""

    name = "master"

    def run(self, ctx: RunContext) -> None:
        assert ctx.spec
        if ctx.spec_only:
            ctx.events.emit("node.task", node=self.name, task="Spec only: nothing to master")
            return
        ctx.events.emit("node.task", node=self.name, task="Mixing narration and music")
        mix = mixer.mix(ctx.run_dir, ctx.spec, narration=ctx.brief.narration)
        ctx.video = mixer.mux(ctx.path("render", "silent.mp4"), mix, ctx.path("video.mp4"))
