from __future__ import annotations

import asyncio

from strands.types.event_loop import Usage

from reelhive.agents.critic import MAX_STORY_REPAIRS, CriticNode, run_gates
from reelhive.core.context import RunContext
from reelhive.nodes.base import FunctionNode, _no_usage
from reelhive.nodes.narrate_node import narrate
from reelhive.nodes.timing_node import apply_timing
from reelhive.visuals.resolver import resolve

MAX_PLAN_REPAIRS = 3  # fixes of the plan in a row (the first from `critic`, more while `recheck` still fails)


class RecheckNode(FunctionNode):
    """Re-voice scenes whose narration the fixer changed, re-time, and run the hard checks again; then, if the story
    hasn't been approved yet, the critic's rubric too, so a repaired plan is judged like any other. A failure reopens
    `fix` for another round while the graph allows it."""

    name = "recheck"

    async def execute(self, ctx: RunContext) -> Usage:
        await asyncio.to_thread(self.run, ctx)
        if not ctx.recheck_passed or ctx.story_reviewed:
            return _no_usage()  # failed its checks (back to `fix`), or the story was already approved
        usage = await CriticNode().review(ctx)
        if ctx.story_reviewed:
            return usage
        if ctx.story_rounds <= MAX_STORY_REPAIRS and ctx.plan_rounds + 1 < MAX_PLAN_REPAIRS:
            self.reopen(ctx)  # the critic's reasons are the failures `fix` works from
            return usage
        # Out of story repairs: go ahead with what passes every hard check, and say what the reviewer still wanted.
        notes = "; ".join(ctx.failures)
        ctx.events.emit("node.task", node=self.name, task=f"Going ahead; the story review still notes: {notes}")
        ctx.story_reviewed, ctx.failures = True, []
        return usage

    @staticmethod
    def reopen(ctx: RunContext) -> None:
        ctx.recheck_passed = False
        ctx.plan_rounds += 1
        ctx.completed.discard("fix")

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
            self.reopen(ctx)
