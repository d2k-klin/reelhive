from __future__ import annotations

from reelhive.agents.critic import scenes_block
from reelhive.agents.plan import ScenePlan, brief_block
from reelhive.core.context import RunContext
from reelhive.nodes.base import AgentNode
from reelhive.nodes.timing_node import target_words


class FixerNode(AgentNode):
    name = "fix"
    tier = "strong"
    prompt = "fixer"
    output = ScenePlan

    def build_prompt(self, ctx: RunContext) -> str:
        assert ctx.spec
        failures = "\n".join(f"- {f}" for f in ctx.failures)
        return (
            f"{brief_block(ctx.brief)}\n\n"
            f"Target: about {target_words(ctx.brief)} narration words in total.\n"
            f"Closing message: {ctx.brief.closing}\n\n"
            f"Current scenes:\n{scenes_block(ctx.spec, ctx.narrated)}\n\nFailures:\n{failures}"
        )

    def apply(self, ctx: RunContext, out: ScenePlan) -> None:
        assert ctx.spec
        before = {s.index: s.model_dump(include={"template", "text", "narration", "feature"}) for s in ctx.spec.scenes}
        old = {s.index: s.narration for s in ctx.spec.scenes}
        ctx.spec.scenes = [p.to_scene(i, p.narration or old.get(i, "")) for i, p in enumerate(out.scenes, start=1)]
        after = {s.index: s.model_dump(include={"template", "text", "narration", "feature"}) for s in ctx.spec.scenes}
        changes = [
            {"scene": i, "before": before.get(i), "after": after.get(i)}
            for i in sorted(before.keys() | after.keys())
            if before.get(i) != after.get(i)
        ]
        ctx.events.emit("fix.diff", node=self.name, changes=changes)
        ctx.events.emit("node.task", node=self.name, task=f"{len(changes)} scenes changed")
