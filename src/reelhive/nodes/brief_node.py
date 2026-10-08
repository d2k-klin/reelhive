from __future__ import annotations

import yaml

from reelhive.core.context import RunContext
from reelhive.levels import LEVELS
from reelhive.nodes.base import FunctionNode


class BriefNode(FunctionNode):
    """Validate the brief, fill the level's defaults and save the normalized copy."""

    name = "brief"

    def run(self, ctx: RunContext) -> None:
        level = LEVELS[ctx.brief.level]
        ctx.brief = ctx.brief.model_copy(update=level.defaults(ctx.brief))
        ctx.events.emit(
            "node.task", node=self.name, task=f"Level {ctx.brief.level}: {len(ctx.brief.features)} features"
        )
        ctx.path("brief.yaml").write_text(yaml.safe_dump(ctx.brief.model_dump(), sort_keys=False))
