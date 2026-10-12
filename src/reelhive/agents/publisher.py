"""`publish`: a social editor who writes the post that goes out with the finished video, per platform.

The output model is built from the platforms chosen for this run, so the model must write exactly one block per
platform, each held to that platform's own limits (schemas/publish.py). Nothing is posted here: the copy waits
for the user's approval, and the posting graph runs only after it.
"""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, create_model
from strands.types.event_loop import Usage

from reelhive.agents.plan import brief_block, research_block
from reelhive.core.context import RunContext
from reelhive.nodes.base import AgentNode
from reelhive.schemas.publish import COPY_MODELS, PostCopy
from reelhive.schemas.scene_spec import CtaScene, display_url

GUIDANCE = {
    "youtube": "YouTube: a searchable title (what it is and for whom, not clickbait); a description whose first two "
    "lines carry the hook and the link, then a few lines on what the video shows; 5-12 lowercase search tags.",
    "linkedin": "LinkedIn: a professional post. Open with one line that earns the click (a problem the audience "
    "recognises), two to four short lines on what changes, the link, then up to 3 hashtags. No emoji walls.",
    "tiktok": "TikTok: a short, conversational caption (one or two lines) with 3-5 relevant hashtags at the end.",
    "instagram": "Instagram Reels: a hook line, one or two short lines, a call to action, then 5-10 hashtags at the "
    "end. Links aren't clickable in captions, so say where to find it (e.g. 'link in bio') instead of a URL.",
}


class PublishCopyNode(AgentNode):
    name = "publish"
    tier = "strong"
    prompt = "publisher"

    async def execute(self, ctx: RunContext) -> Usage:
        assert ctx.publish
        fields: dict[str, Any] = {p: (COPY_MODELS[p], ...) for p in ctx.publish.platforms}
        self.output = create_model("PostCopy", __config__=ConfigDict(extra="forbid"), **fields)
        return await super().execute(ctx)

    def build_prompt(self, ctx: RunContext) -> str:
        assert ctx.spec and ctx.publish
        closing = next((s for s in reversed(ctx.spec.scenes) if isinstance(s, CtaScene)), None)
        link = ctx.brief.cta_url or ctx.brief.website
        story = "\n".join(f"{s.index}. {s.narration}" for s in ctx.spec.scenes)
        intro = ctx.spec.intro
        settings = ctx.config.publishing
        notes = []
        if "tiktok" in ctx.publish.platforms and settings.tiktok.mode == "draft":
            notes.append("TikTok goes to the creator's inbox as a draft: the caption is pasted in by hand.")
        if "youtube" in ctx.publish.platforms:
            notes.append(f"YouTube privacy: {settings.youtube.privacy}.")
        return (
            f"{brief_block(ctx.brief)}{research_block(ctx)}\n\n"
            f"The finished video: {ctx.spec.duration:.0f}s, {ctx.spec.format}, with English subtitles.\n"
            + (
                f"Title screen: {intro.title}" + (f" — {intro.tagline}" if intro.tagline else "") + "\n"
                if intro
                else ""
            )
            + (f"Closing call to action on screen: {closing.text.headline}\n" if closing else "")
            + (f"Link: {link} (shown as {display_url(link)})\n" if link else "No link was given; don't invent one.\n")
            + f"\nNarration, scene by scene:\n{story}\n\n"
            + "Write one post for each of: "
            + ", ".join(ctx.publish.platforms)
            + ".\n"
            + "\n".join(GUIDANCE[p] for p in ctx.publish.platforms)
            + ("\n" + " ".join(notes) if notes else "")
        )

    def apply(self, ctx: RunContext, out: Any) -> None:
        assert ctx.publish
        ctx.publish.posts = PostCopy.model_validate(out.model_dump())
        ctx.events.emit(
            "node.task", node=self.name, task="Drafted posts for " + ", ".join(ctx.publish.posts.platforms())
        )
