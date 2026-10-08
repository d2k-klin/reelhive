from __future__ import annotations

from reelhive.agents.plan import brief_block
from reelhive.core.context import RunContext
from reelhive.nodes.base import AgentNode
from reelhive.nodes.timing_node import target_words
from reelhive.schemas.script import Script


class ScriptWriterNode(AgentNode):
    name = "script"
    tier = "strong"
    prompt = "script_writer"
    output = Script

    def build_prompt(self, ctx: RunContext) -> str:
        return (
            f"{brief_block(ctx.brief)}\n\n"
            f"Target: about {target_words(ctx.brief)} words in total across all beats.\n"
            f"Closing message, to end the final beat verbatim: {ctx.brief.closing}\nEditing note: {ctx.note}"
        )

    def apply(self, ctx: RunContext, out: Script) -> None:
        ctx.script = out
        ctx.path("script.json").write_text(out.model_dump_json(indent=2))
        ctx.events.emit("node.task", node=self.name, task=f"{len(out.beats)} beats written")
