from __future__ import annotations

from pathlib import Path

import yaml

from reelhive.core.context import RunContext
from reelhive.levels import LEVELS
from reelhive.nodes.base import FunctionNode


class BriefNode(FunctionNode):
    """Validate the brief, fill the level's defaults and save the normalized copy."""

    name = "brief"

    def run(self, ctx: RunContext) -> None:
        level = LEVELS[ctx.brief.level]
        ctx.brief = ctx.brief.model_copy(update=level.defaults(ctx.brief), deep=True)
        # Persist absolute source paths so approval can resume from another directory.
        if ctx.brief.brand.logo:
            ctx.brief.brand.logo = str(Path(ctx.brief.brand.logo).resolve())
        sources = ctx.brief.visuals
        if sources.screenshots and sources.screenshots.storage_state:
            sources.screenshots.storage_state = str(Path(sources.screenshots.storage_state).resolve())
        from reelhive.schemas.brief import Images

        if isinstance(sources.images, Images):
            sources.images.dir = str(Path(sources.images.dir).resolve())
            if sources.images.captions:
                sources.images.captions = str(Path(sources.images.captions).resolve())
        ctx.events.emit(
            "node.task", node=self.name, task=f"Level {ctx.brief.level}: {len(ctx.brief.features)} features"
        )
        ctx.path("brief.yaml").write_text(yaml.safe_dump(ctx.brief.model_dump(), sort_keys=False))
