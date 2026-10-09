"""Draft graph: brief -> research -> script (plan §3.1). Approval stops sit after this graph."""

from __future__ import annotations

from strands.multiagent.graph import Graph, GraphBuilder

from reelhive.agents.researcher import ResearchNode
from reelhive.agents.script_writer import ScriptWriterNode
from reelhive.nodes.brief_node import BriefNode


def build_draft_graph() -> Graph:
    b = GraphBuilder()
    b.add_node(BriefNode(), "brief")
    b.add_node(ResearchNode(), "research")
    b.add_node(ScriptWriterNode(), "script")
    b.add_edge("brief", "research")
    b.add_edge("research", "script")
    b.set_entry_point("brief")
    b.set_max_node_executions(3)
    return b.build()
