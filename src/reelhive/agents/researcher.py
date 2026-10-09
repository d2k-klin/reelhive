"""`research`: read the product website and turn it into product notes the writers build on.

Runs between `brief` and `script` when the brief has a `website`. The crawl is the screenshot crawler's:
same origin only, at most 10 pages, masked selectors removed, saved login state honoured. Page text goes
to the configured provider (it stays local with Ollama). Without a website the step is skipped.
"""

from __future__ import annotations

import asyncio
import json

from pydantic import BaseModel, Field
from strands.types.event_loop import Usage

from reelhive.agents.plan import brief_block
from reelhive.core.context import RunContext
from reelhive.nodes.base import AgentNode, _no_usage
from reelhive.schemas.brief import Screenshots


class ProductNotes(BaseModel):
    product: str = Field(description="What the product is and who it is for, in one or two sentences")
    names: list[str] = Field(default_factory=list, description="Names exactly as the website spells them")
    offerings: list[str] = Field(default_factory=list)
    audience_pains: list[str] = Field(default_factory=list)
    proof_points: list[str] = Field(default_factory=list, description="Facts from the website only")
    note_readings: list[str] = Field(default_factory=list, description="One per brief key point, same order")


def site_options(ctx: RunContext) -> Screenshots:
    """Reuse the screenshot settings (login state, masks) when they point at the same site."""
    shots = ctx.brief.visuals.screenshots
    if shots and shots.url.rstrip("/") == (ctx.brief.website or "").rstrip("/"):
        return shots
    return Screenshots(url=ctx.brief.website or "")


class ResearchNode(AgentNode):
    name = "research"
    tier = "fast"
    prompt = "researcher"
    output = ProductNotes

    async def execute(self, ctx: RunContext) -> Usage:
        if not ctx.brief.website:
            ctx.events.emit("node.task", node=self.name, task="No product website given; writing from the brief")
            return _no_usage()
        from reelhive.visuals.capture import discover

        ctx.events.emit("node.task", node=self.name, task=f"Reading {ctx.brief.website}")
        try:
            pages = await asyncio.to_thread(discover, site_options(ctx), ctx.brief.format, True)
        except Exception as error:  # an unreachable site must not stop the video
            ctx.events.emit("node.task", node=self.name, task=f"Could not read the website: {error}")
            return _no_usage()
        ctx.site_pages = [p for p in pages if p.get("text")]
        if not ctx.site_pages:
            ctx.events.emit("node.task", node=self.name, task="The website had no readable text")
            return _no_usage()
        ctx.events.emit("node.task", node=self.name, task=f"Read {len(ctx.site_pages)} pages")
        return await super().execute(ctx)

    def build_prompt(self, ctx: RunContext) -> str:
        pages = "\n\n".join(f"## {p['title']} ({p['route']})\n{p['text']}" for p in ctx.site_pages)
        return f"{brief_block(ctx.brief)}\n\nWebsite pages:\n{pages}"

    def apply(self, ctx: RunContext, out: ProductNotes) -> None:
        ctx.research = out.model_dump()
        ctx.path("research.json").write_text(json.dumps(ctx.research, indent=2))
        ctx.events.emit("node.task", node=self.name, task=f"Product notes ready: {out.product[:80]}")
