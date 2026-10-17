from __future__ import annotations

from reelhive.agents.critic import run_gates
from reelhive.core.context import RunContext
from reelhive.nodes.base import FunctionNode
from reelhive.nodes.narrate_node import narrate
from reelhive.nodes.timing_node import apply_timing
from reelhive.visuals.resolver import resolve


class RecheckNode(FunctionNode):
    """Re-voice scenes whose narration the fixer changed, re-time, and run the hard checks again. A failure reopens
    `fix` for another round while the graph allows it."""

    name = "recheck"

    def run(self, ctx: RunContext) -> None:
        assert ctx.spec
        changed = [
            s
            for s in ctx.spec.scenes
            if ctx.narrated.get(s.index, ("",))[0] != s.narration
            or ctx.voiced.get(s.index) != (s.voice_override or ctx.brief.voice).record()
        ]
        for n, scene in enumerate(changed, start=1):
            ctx.events.emit(
                "node.task", node=self.name, task=f"Re-voicing scene {scene.index}", done=n - 1, total=len(changed)
            )
            narrate(ctx, scene.index, scene.narration)
        resolve(ctx)
        apply_timing(ctx.spec, ctx.narrated, ctx.brief, ctx.words)
        ctx.failures = run_gates(ctx, self.name)
        ctx.recheck_passed = not ctx.failures
        if ctx.failures:
            # A near miss (a shot 0.1 s too long) gets another repair rather than stopping the run; the graph
            # bounds how many (MAX_PLAN_REPAIRS).
            ctx.plan_rounds += 1
            ctx.completed.discard("fix")
