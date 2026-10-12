# `graphs`

**Overview.** The two Strands graphs, and nothing but their topology. Nodes do the work; these files only say which node runs after which, and on what condition. They are the best place to see the whole pipeline at a glance.

## What's here

| File | Graph |
| --- | --- |
| [`draft.py`](draft.py) | `brief ─► research ─► script`. Always runs. Approval stops (medium) happen after it. |
| [`publish.py`](publish.py) | Two graphs with a human approval between them. The copy graph: `ready ─(gates pass)─► publish`. The post graph: `ready` fanning out to one `post_<platform>` node per chosen platform, in parallel. `ready` runs in both, because accounts and settings can change between drafting and approval. |
| [`production.py`](production.py) | `scenes ─► visuals`, `narrate` and `music` in parallel, fan-in to `timing`, then `critic` with a conditional `fix ─► recheck` path, `render`, `review` (which can loop back to `fix`), `sound` and `master`. Also exports `NODES` (used to report skipped nodes), `FINISHING` (what an edit reopens) and the edge conditions. `build_production_graph(stage)` builds the whole graph (`"all"`), or for `high` just the preparation half (`"prepare"`: up to `timing`, then the scene stop) and the finishing half (`"finish"`: `critic` onward, after `approve-scenes`). |

```
production:   ┌─► scenes ─► visuals ─┐
              ├─► narrate ───────────┼─► timing ─► critic ─┬─(pass)──────────────────────► render ─► review ─┬─(pass)─► sound ─► master
              └─► music ─────────────┘                     └─(fail)─► fix ─► recheck ─(pass)─┘                │
                                                                      ▲                                       │
                                                                      └──────────(fail, rounds left)──────────┘
```

## Things that are not obvious

- Strands runs a node as soon as **any** incoming edge is satisfied. The fan-in to `timing` therefore uses `all_branches_done` on each of its three edges.
- `render` and `fix` each have two conditional incoming edges (`render`: critic passed, recheck passed; `fix`: critic failed, review failed with rounds left). If `recheck` fails, or the review still fails after `MAX_REVIEW_ROUNDS`, nothing is ready, the graph ends, and the service reports the failures.
- Conditions read the run through `invocation_state["ctx"]`; a condition opts in by having an `invocation_state` keyword parameter.
- The review loop is a real cycle. `reset_on_revisit(True)` lets Strands run a node again; the run's checkpoint says what is done, so the node that makes a result stale reopens it there (a failed review reopens `fix`, `recheck` and `render`; a new render reopens `review`, `sound` and `master`). The edges read `review_passed` and `review_rounds`, so a run resumed at `critic` goes back into the repair loop instead of re-rendering an unrepaired cut. `set_max_node_executions` allows exactly the bounded rounds.

## Extending

1. Write the node (see [`../nodes/README.md`](../nodes/README.md) or [`../agents/README.md`](../agents/README.md)).
2. `b.add_node(MyNode(), MyNode.name)` and wire its edges here. If it joins a fan-in, update `BRANCHES` / the condition.
3. Add the name to `NODES` so a run that skips it reports `node.skipped`.
4. Extend the expected node order in `tests/integration/test_graphs.py`.

See also: [docs/strands-graph.md](../../../docs/strands-graph.md), the learning notes for this design.
