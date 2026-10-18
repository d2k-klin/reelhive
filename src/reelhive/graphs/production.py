"""Production graph (plan §3.1).

    ┌─► scenes ─► visuals ─┐
    ├─► narrate ┼─► timing ─► critic ─┬─(pass)──────────────────────► render ─► review ─┬─(pass)─► sound ─► master
    └─► music ──┘                     └─(fail)─► fix ⇄ recheck ─(pass)─┘                │
                                                 ▲   (fail, repairs left)                │
                                                 └──────────(fail, rounds left)──────────┘

`critic` judges the plan before anything is drawn; `review` judges the cut the renderer actually drew
(measured layout, and optionally the frames themselves), and sends it back through `fix` when it falls
short. `sound` scores the approved cut on the moments the renderer reported, so it runs once, after the loop.
Strands runs a node as soon as ANY incoming edge is satisfied, so:
  * the fan-in to `timing` uses a condition that waits for all three branches;
  * `render` has two conditional incoming edges and `fix` three (critic, recheck and review failures);
  * a plan that still fails after `fix` goes round again while MAX_PLAN_REPAIRS allows;
  * the review loop is a real cycle: the graph resets revisited nodes, `review` reopens the repair path in
    the run's checkpoint, and `MAX_REVIEW_ROUNDS` plus the execution cap bound it.
If recheck still fails after the last repair, or the review after its last round, nothing is ready to run, the
graph ends, and the service stops the run with the failure report.
"""

from __future__ import annotations

from typing import Any

from strands.multiagent.graph import Graph, GraphBuilder, GraphState

from reelhive.agents.critic import CriticNode
from reelhive.agents.fixer import FixerNode
from reelhive.agents.music_director import MusicDirectorNode
from reelhive.agents.reviewer import MAX_REVIEW_ROUNDS, ReviewNode
from reelhive.agents.scene_planner import ScenePlannerNode
from reelhive.agents.sound_designer import SoundDesignerNode
from reelhive.nodes.master_node import MasterNode
from reelhive.nodes.narrate_node import NarrateNode
from reelhive.nodes.recheck_node import MAX_PLAN_REPAIRS, RecheckNode
from reelhive.nodes.render_node import RenderNode
from reelhive.nodes.timing_node import TimingNode
from reelhive.nodes.visuals_node import VisualsNode

BRANCHES = ("visuals", "narrate", "music")
FINISHING = ("critic", "fix", "recheck", "render", "review", "sound", "master")
NODES = ("scenes", *BRANCHES, "timing", *FINISHING)
REPAIR_LOOP = ("fix", "recheck", "render", "review")


def all_branches_done(state: GraphState) -> bool:
    done = {n.node_id for n in state.completed_nodes}
    return set(BRANCHES) <= done


def _ctx(invocation_state: dict[str, Any]) -> Any:
    return invocation_state["ctx"]


def critic_passed(state: GraphState, *, invocation_state: dict[str, Any], **_: Any) -> bool:
    """Plan approved and no rendered cut awaiting repair (a resumed run re-enters at `critic`)."""
    ctx = _ctx(invocation_state)
    return bool(ctx.critic_passed) and ctx.review_passed is not False


def _repair_due(ctx: Any) -> bool:
    """The cut failed review and a repair round is left."""
    return ctx.review_passed is False and ctx.review_rounds <= MAX_REVIEW_ROUNDS


def critic_failed(state: GraphState, *, invocation_state: dict[str, Any], **_: Any) -> bool:
    ctx = _ctx(invocation_state)
    return not ctx.critic_passed or _repair_due(ctx)


def recheck_passed(state: GraphState, *, invocation_state: dict[str, Any], **_: Any) -> bool:
    return bool(_ctx(invocation_state).recheck_passed)


def recheck_failed(state: GraphState, *, invocation_state: dict[str, Any], **_: Any) -> bool:
    """The repaired plan still fails its checks and another repair is allowed."""
    ctx = _ctx(invocation_state)
    return not ctx.recheck_passed and ctx.plan_rounds < MAX_PLAN_REPAIRS


def review_passed(state: GraphState, *, invocation_state: dict[str, Any], **_: Any) -> bool:
    return _ctx(invocation_state).review_passed is True


def review_failed(state: GraphState, *, invocation_state: dict[str, Any], **_: Any) -> bool:
    return _repair_due(_ctx(invocation_state))


def build_production_graph(stage: str = "all") -> Graph:
    b = GraphBuilder()
    preparation = (ScenePlannerNode(), VisualsNode(), NarrateNode(), MusicDirectorNode(), TimingNode())
    finishing = (
        CriticNode(),
        FixerNode(),
        RecheckNode(),
        RenderNode(),
        ReviewNode(),
        SoundDesignerNode(),
        MasterNode(),
    )
    for node in preparation if stage == "prepare" else finishing if stage == "finish" else preparation + finishing:
        b.add_node(node, node.name)
    if stage != "finish":
        for branch in BRANCHES:
            b.set_entry_point("scenes" if branch == "visuals" else branch)
            b.add_edge(branch, "timing", condition=all_branches_done)
        b.add_edge("scenes", "visuals")
    else:
        b.set_entry_point("critic")
    if stage == "all":
        b.add_edge("timing", "critic")
    if stage != "prepare":
        b.add_edge("critic", "render", condition=critic_passed)
        b.add_edge("critic", "fix", condition=critic_failed)
        b.add_edge("fix", "recheck")
        b.add_edge("recheck", "render", condition=recheck_passed)
        b.add_edge("recheck", "fix", condition=recheck_failed)
        b.add_edge("render", "review")
        b.add_edge("review", "sound", condition=review_passed)
        b.add_edge("sound", "master")
        b.add_edge("review", "fix", condition=review_failed)
        b.reset_on_revisit(True)
    b.set_max_node_executions(len(NODES) + MAX_REVIEW_ROUNDS * len(REPAIR_LOOP) + MAX_PLAN_REPAIRS * 2)
    return b.build()
