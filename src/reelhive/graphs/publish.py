"""Publishing graphs. A post goes out under the user's name, so a human approves the copy between the two.

    copy:  ready ─(gates pass)─► publish                    (drafts the post copy per platform)

    post:  ready ─(gates pass)─┬─► post_youtube
                               ├─► post_linkedin             (in parallel; each records its own result)
                               ├─► post_tiktok
                               └─► post_instagram

`ready` runs in both: accounts and settings can change between drafting and the approval. When it fails, no edge
is satisfied and the graph ends with the job blocked and its failures, before any model call or upload.
"""

from __future__ import annotations

from typing import Any

from strands.multiagent.graph import Graph, GraphBuilder, GraphState

from reelhive.agents.publisher import PublishCopyNode
from reelhive.nodes.publish_nodes import POST_NODES, ReadyNode
from reelhive.schemas.publish import Platform

COPY_NODES = ("ready", "publish")


def post_names(platforms: list[Platform]) -> list[str]:
    return [POST_NODES[p].name for p in platforms]


def ready_passed(state: GraphState, *, invocation_state: dict[str, Any], **_: Any) -> bool:
    job = invocation_state["ctx"].publish
    return job is not None and not job.failures


def build_copy_graph() -> Graph:
    b = GraphBuilder()
    b.add_node(ReadyNode(), "ready")
    b.add_node(PublishCopyNode(), "publish")
    b.add_edge("ready", "publish", condition=ready_passed)
    b.set_entry_point("ready")
    b.set_max_node_executions(len(COPY_NODES))
    return b.build()


def build_post_graph(platforms: list[Platform]) -> Graph:
    b = GraphBuilder()
    b.add_node(ReadyNode(), "ready")
    for platform in platforms:
        node = POST_NODES[platform]()
        b.add_node(node, node.name)
        b.add_edge("ready", node.name, condition=ready_passed)
    b.set_entry_point("ready")
    b.set_max_node_executions(1 + len(platforms))
    return b.build()
