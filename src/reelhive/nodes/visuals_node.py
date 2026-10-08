from reelhive.core.context import RunContext
from reelhive.nodes.base import FunctionNode
from reelhive.visuals.resolver import resolve


class VisualsNode(FunctionNode):
    name = "visuals"

    def run(self, ctx: RunContext) -> None:
        resolve(ctx)
