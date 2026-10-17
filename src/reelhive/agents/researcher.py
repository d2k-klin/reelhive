"""`research`: read the product website and documents and turn them into product notes the writers build on.

Runs between `brief` and `script` when the brief has a `website` (or a public screenshot URL) or
`documents`. The crawl is the screenshot crawler's: same origin only, at most 10 pages, masked selectors
removed, saved login state honoured. Documents are PDFs or decks, read page by page. Page text goes to
the configured provider (it stays local with Ollama). With none of them the step is skipped.
"""

from __future__ import annotations

import asyncio
import json
from urllib.parse import urlparse

from pydantic import BaseModel, Field
from strands.types.event_loop import Usage

from reelhive.agents.plan import brief_block
from reelhive.core.context import RunContext
from reelhive.nodes.base import AgentNode, _no_usage
from reelhive.schemas.brief import Screenshots
from reelhive.visuals import products


class ProductNotes(BaseModel):
    product: str = Field(description="What the product is and who it is for, in one or two sentences")
    names: list[str] = Field(default_factory=list, description="Names exactly as the website spells them")
    offerings: list[str] = Field(default_factory=list)
    audience_pains: list[str] = Field(default_factory=list)
    proof_points: list[str] = Field(default_factory=list, description="Facts from the sources only")
    note_readings: list[str] = Field(default_factory=list, description="One per brief key point, same order")


def site_options(ctx: RunContext) -> Screenshots | None:
    """The website to read: the brief's `website`, else a public screenshot URL. Reuses the screenshot
    settings (login state, masks) when they point at the same site. Local dev apps are never sent."""
    shots = ctx.brief.visuals.screenshots
    website = ctx.brief.website
    if not website and shots:
        host = urlparse(shots.url).hostname or ""
        if host not in ("localhost", "127.0.0.1", "::1") and not host.endswith((".localhost", ".test", ".local")):
            website = shots.url
    if not website:
        return None
    if shots and shots.url.rstrip("/") == website.rstrip("/"):
        return shots
    return Screenshots(url=website)


class ResearchNode(AgentNode):
    name = "research"
    tier = "fast"
    prompt = "researcher"
    output = ProductNotes

    async def execute(self, ctx: RunContext) -> Usage:
        seeded = ctx.run_dir / "research.json"
        if ctx.research is None and seeded.exists():  # a cut carries its parent's research over
            ctx.research = json.loads(seeded.read_text())
            ctx.events.emit("node.task", node=self.name, task="Using the research of the original video")
            return _no_usage()
        site = site_options(ctx)
        ctx.site_pages = []
        if site:
            from reelhive.visuals.capture import discover

            ctx.events.emit("node.task", node=self.name, task=f"Reading {site.url}")
            try:
                pages = await asyncio.to_thread(discover, site, ctx.brief.format, True)
                ctx.site_pages += [p for p in pages if p.get("text")]
                await self._products(ctx, pages)
            except Exception as error:  # an unreachable site must not stop the video
                ctx.events.emit("node.task", node=self.name, task=f"Could not read the website: {error}")
        if ctx.brief.documents:
            from reelhive.visuals.documents import pages as document_pages

            ctx.events.emit("node.task", node=self.name, task=f"Reading {len(ctx.brief.documents)} documents")
            try:
                found = await asyncio.to_thread(document_pages, ctx.brief.documents, ctx.run_dir / "documents")
                ctx.site_pages += [
                    {"title": f"{p['document']}, page {p['page']}", "route": p["document"], "text": p["text"]}
                    for p in found
                    if p["text"]
                ]
            except Exception as error:  # a broken file must not stop the video either
                ctx.events.emit("node.task", node=self.name, task=f"Could not read the documents: {error}")
        if not ctx.site_pages:
            ctx.events.emit("node.task", node=self.name, task="Nothing readable to research; writing from the brief")
            return _no_usage()
        ctx.events.emit("node.task", node=self.name, task=f"Read {len(ctx.site_pages)} pages")
        return await super().execute(ctx)

    async def _products(self, ctx: RunContext, pages: list[dict]) -> None:
        """The site's own product data (price, rating, reviews) as facts, and its product photos as images."""
        ctx.products = products.collect(pages)
        if not ctx.products:
            return
        names = ", ".join(p["name"] for p in ctx.products)
        ctx.events.emit("node.task", node=self.name, task=f"Product data for {names}")
        if ctx.brief.visuals.source in ("auto", "images"):
            skipped = await asyncio.to_thread(products.save_photos, ctx.products, ctx.path("visuals", "product"))
            for reason in skipped:
                ctx.events.emit("node.task", node=self.name, task=f"Product photo skipped: {reason}")

    def build_prompt(self, ctx: RunContext) -> str:
        pages = "\n\n".join(f"## {p['title']} ({p['route']})\n{p['text']}" for p in ctx.site_pages)
        return f"{brief_block(ctx.brief)}\n\nSource pages (the product website and the user's documents):\n{pages}"

    def apply(self, ctx: RunContext, out: ProductNotes) -> None:
        # The structured facts are the site's own words, kept beside the notes so writers and the critic can use them.
        ctx.research = out.model_dump() | ({"products": ctx.products} if ctx.products else {})
        ctx.path("research.json").write_text(json.dumps(ctx.research, indent=2))
        ctx.events.emit("node.task", node=self.name, task=f"Product notes ready: {out.product[:80]}")
