# `graphs`

**Overview.** The two Strands graphs, and nothing but their topology. Nodes do the work; these files only say which node runs after which, and on what condition. They are the best place to see the whole pipeline at a glance.

## What's here

| File | Graph |
| --- | --- |
| [`draft.py`](draft.py) | `brief ─► script`. Always runs. Approval stops (medium) happen after it. |
| [`production.py`](production.py) | `scenes ─► visuals`, `narrate` and `music` in parallel, fan-in to `timing`, then `critic` with a conditional `fix ─► recheck` path, and `render`. Also exports `NODES` (used to report skipped nodes) and the edge conditions. `build_production_graph(stage)` builds the whole graph (`"all"`), or for `high` just the preparation half (`"prepare"`: up to `timing`, then the scene stop) and the finishing half (`"finish"`: `critic` onward, after `approve-scenes`). |

```
production:   ┌─► scenes ─► visuals ─┐
              ├─► narrate ───────────┼─► timing ─► critic ─┬─(pass)─────────────────────► render
              └─► music ─────────────┘                     └─(fail)─► fix ─► recheck ─(pass)─┘
```

## Things that are not obvious

- Strands runs a node as soon as **any** incoming edge is satisfied. The fan-in to `timing` therefore uses `all_branches_done` on each of its three edges.
- `render` is one node with two conditional incoming edges (critic passed, recheck passed). If `recheck` fails, nothing is ready, the graph ends, and the service reports the failures.
- Conditions read the run through `invocation_state["ctx"]`; a condition opts in by having an `invocation_state` keyword parameter.
- `set_max_node_executions` is a guard; the graph has no cycles.

## Extending

1. Write the node (see [`../nodes/README.md`](../nodes/README.md) or [`../agents/README.md`](../agents/README.md)).
2. `b.add_node(MyNode(), MyNode.name)` and wire its edges here. If it joins a fan-in, update `BRANCHES` / the condition.
3. Add the name to `NODES` so a run that skips it reports `node.skipped`.
4. Extend the expected node order in `tests/integration/test_graphs.py`.

See also: [docs/strands-graph.md](../../../docs/strands-graph.md), the learning notes for this design.
