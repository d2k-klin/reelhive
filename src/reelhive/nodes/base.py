"""Custom Strands graph nodes (plan §3.2).

Every ReelHive node subclasses MultiAgentBase, so the graph treats deterministic work (TTS,
timing, rendering) and agent work the same way, and every node emits the same events.
"""

from __future__ import annotations

import asyncio
import time
from importlib.resources import files
from typing import Any, ClassVar

from pydantic import BaseModel
from strands import Agent
from strands.multiagent.base import MultiAgentBase, MultiAgentResult, Status
from strands.types.event_loop import Usage

from reelhive.core.context import RunContext


def _no_usage() -> Usage:
    return Usage(inputTokens=0, outputTokens=0, totalTokens=0)


class FunctionNode(MultiAgentBase):
    """A deterministic node: override `run`, which executes in a worker thread."""

    name: ClassVar[str]

    def __init__(self) -> None:
        super().__init__()
        self.id = self.name

    def run(self, ctx: RunContext) -> None:
        raise NotImplementedError

    async def execute(self, ctx: RunContext) -> Usage:
        await asyncio.to_thread(self.run, ctx)
        return _no_usage()

    async def invoke_async(
        self, task: Any, invocation_state: dict[str, Any] | None = None, **kwargs: Any
    ) -> MultiAgentResult:
        ctx: RunContext = (invocation_state or {})["ctx"]
        ctx.events.emit("node.started", node=self.name)
        started = time.time()
        try:
            usage = await self.execute(ctx)
        except Exception as e:
            ctx.events.emit(
                "node.finished", node=self.name, status="failed", error=str(e), seconds=round(time.time() - started, 2)
            )
            raise
        ctx.events.emit(
            "node.finished",
            node=self.name,
            status="completed",
            seconds=round(time.time() - started, 2),
            tokens=usage["totalTokens"],
        )
        return MultiAgentResult(status=Status.COMPLETED, accumulated_usage=usage)


def load_prompt(name: str) -> str:
    return files("reelhive.agents.prompts").joinpath(f"{name}.md").read_text()


class AgentNode(FunctionNode):
    """An LLM node: builds a prompt from the run, gets validated structured output, applies it."""

    tier: ClassVar[str] = "strong"  # "strong" | "fast"
    prompt: ClassVar[str]  # agents/prompts/<prompt>.md
    output: ClassVar[type[BaseModel]]

    def build_prompt(self, ctx: RunContext) -> str:
        raise NotImplementedError

    def apply(self, ctx: RunContext, out: Any) -> None:
        raise NotImplementedError

    async def execute(self, ctx: RunContext) -> Usage:
        def stream(**event: Any) -> None:
            if isinstance(event.get("data"), str):
                ctx.events.emit("agent.text", node=self.name, text=event["data"])

        agent = Agent(model=ctx.models[self.tier], system_prompt=load_prompt(self.prompt), callback_handler=stream)
        result = await agent.invoke_async(self.build_prompt(ctx), structured_output_model=self.output)
        await asyncio.to_thread(self.apply, ctx, result.structured_output)
        return result.metrics.accumulated_usage
