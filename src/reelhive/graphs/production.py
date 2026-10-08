"""Production graph (plan §3.1).

    ┌─► scenes ─► visuals ─┐
    ├─► narrate ┼─► timing ─► critic ─┬─(pass)────────────────────► render
    └─► music ──┘                     └─(fail)─► fix ─► recheck ─(pass)─┘

Strands runs a node as soon as ANY incoming edge is satisfied, so:
  * the fan-in to `timing` uses a condition that waits for all three branches;
  * `render` is one node with two conditional incoming edges (critic pass, recheck pass).
If recheck fails, nothing is ready to run, the graph ends, and the service reports why.
"""

from __future__ import annotations

from typing import Any

from strands.multiagent.graph import Graph, GraphBuilder, GraphState

from reelhive.agents.critic import CriticNode
from reelhive.agents.fixer import FixerNode
from reelhive.agents.music_director import MusicDirectorNode
from reelhive.agents.scene_planner import ScenePlannerNode
from reelhive.nodes.narrate_node import NarrateNode
from reelhive.nodes.recheck_node import RecheckNode
from reelhive.nodes.render_node import RenderNode
from reelhive.nodes.timing_node import TimingNode
from reelhive.nodes.visuals_node import VisualsNode

BRANCHES = ("visuals", "narrate", "music")
NODES = ("scenes", *BRANCHES, "timing", "critic", "fix", "recheck", "render")


def all_branches_done(state: GraphState) -> bool:
    done = {n.node_id for n in state.completed_nodes}
    return set(BRANCHES) <= done


def critic_passed(state: GraphState, *, invocation_state: dict[str, Any], **_: Any) -> bool:
    return bool(invocation_state["ctx"].critic_passed)


def critic_failed(state: GraphState, *, invocation_state: dict[str, Any], **_: Any) -> bool:
    return not invocation_state["ctx"].critic_passed


def recheck_passed(state: GraphState, *, invocation_state: dict[str, Any], **_: Any) -> bool:
    return bool(invocation_state["ctx"].recheck_passed)


def build_production_graph() -> Graph:
    b = GraphBuilder()
    for node in (
        ScenePlannerNode(),
        VisualsNode(),
        NarrateNode(),
        MusicDirectorNode(),
        TimingNode(),
        CriticNode(),
        FixerNode(),
        RecheckNode(),
        RenderNode(),
    ):
        b.add_node(node, node.name)
    for branch in BRANCHES:
        b.set_entry_point("scenes" if branch == "visuals" else branch)
        b.add_edge(branch, "timing", condition=all_branches_done)
    b.add_edge("scenes", "visuals")
    b.add_edge("timing", "critic")
    b.add_edge("critic", "render", condition=critic_passed)
    b.add_edge("critic", "fix", condition=critic_failed)
    b.add_edge("fix", "recheck")
    b.add_edge("recheck", "render", condition=recheck_passed)
    b.set_max_node_executions(len(NODES))
    return b.build()
