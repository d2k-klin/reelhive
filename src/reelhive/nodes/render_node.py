from __future__ import annotations

from reelhive.audio import mixer
from reelhive.core.context import RunContext
from reelhive.nodes.base import FunctionNode


class RenderNode(FunctionNode):
    """Render the silent video with Revideo, then mix, duck and mux the audio with ffmpeg."""

    name = "render"

    def run(self, ctx: RunContext) -> None:
        assert ctx.spec
        spec_path = ctx.path("spec.json")
        spec_path.write_text(ctx.spec.model_dump_json(indent=2))
        if ctx.spec_only:
            ctx.events.emit("node.task", node=self.name, task="Spec only: video rendering skipped")
            return

        last = {"percent": -1}

        def progress(p: float) -> None:
            # Revideo reports every frame; log whole percents only (a 90s video was ~2,700 events per render).
            percent = int(p * 100)
            if percent != last["percent"]:
                last["percent"] = percent
                task = "Finalizing video frames" if p >= 1 else "Rendering frames"
                ctx.events.emit("node.task", node=self.name, task=task, progress=round(p, 3))

        silent = ctx.path("render", "silent.mp4")
        ctx.renderer(spec_path, silent, progress)

        ctx.events.emit("node.task", node=self.name, task="Mixing narration and music")
        mix = mixer.mix(ctx.run_dir, ctx.spec)
        ctx.video = mixer.mux(silent, mix, ctx.path("video.mp4"))
