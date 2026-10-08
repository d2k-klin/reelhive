from __future__ import annotations

from reelhive.agents.critic import run_gates
from reelhive.core.context import RunContext
from reelhive.nodes.base import FunctionNode
from reelhive.nodes.narrate_node import narrate
from reelhive.nodes.timing_node import apply_timing


class RecheckNode(FunctionNode):
    """Re-voice scenes whose narration the fixer changed, re-time, and run the hard checks again."""

    name = "recheck"

    def run(self, ctx: RunContext) -> None:
        assert ctx.spec
        changed = [s for s in ctx.spec.scenes if ctx.narrated.get(s.index, ("",))[0] != s.narration]
        for n, scene in enumerate(changed, start=1):
            ctx.events.emit(
                "node.task", node=self.name, task=f"Re-voicing scene {scene.index}", done=n - 1, total=len(changed)
            )
            narrate(ctx, scene.index, scene.narration)
        apply_timing(ctx.spec, ctx.narrated, ctx.brief)
        ctx.failures = run_gates(ctx, self.name)
        ctx.recheck_passed = not ctx.failures
