from __future__ import annotations

from reelhive.audio import mixer
from reelhive.core.context import RunContext
from reelhive.nodes.base import FunctionNode
from reelhive.render import subtitles


class MasterNode(FunctionNode):
    """Mix narration, music and sound effects (ducking the music under the voice), mux them onto the reviewed cut,
    and write the subtitles: `video.srt`/`video.vtt` beside the video and a soft track inside it."""

    name = "master"

    def run(self, ctx: RunContext) -> None:
        assert ctx.spec
        if ctx.spec_only:
            ctx.events.emit("node.task", node=self.name, task="Spec only: nothing to master")
            return
        ctx.events.emit("node.task", node=self.name, task="Mixing the soundtrack")
        mix = mixer.mix(ctx.run_dir, ctx.spec, narration=ctx.brief.narration)
        video = ctx.path("video.mp4")
        written = subtitles.write(ctx.spec, video, voiced=ctx.brief.narration)
        if written:
            ctx.events.emit("node.task", node=self.name, task="Subtitles: " + ", ".join(p.name for p in written))
        silent = ctx.path("render", "silent.mp4")
        ctx.video = mixer.mux(silent, mix, video, written[0] if written else None, duration=ctx.spec.duration)
