---
name: strands-graph
description: "Design, implement, debug, or test workflows built with Strands Agents Graph, including custom nodes, parallel branches, conditional edges, shared state, routing, retries, and graph execution. Use when working with strands-agents, MultiAgentBase, GraphBuilder, graph nodes, or agent orchestration."
---

# Strands Graph

Use this workflow for any repository built on Strands Agents Graph.

## Procedure

1. Inspect the pinned `strands-agents` version and the nearest existing graph, node, and test before changing behavior.
2. Draw the intended data flow first: inputs, outputs, parallel branches, joins, conditional routes, retries, and terminal states.
3. Keep orchestration separate from work:
   - graph modules define topology and routing;
   - agent nodes handle model-backed decisions;
   - deterministic nodes handle validation, I/O, transforms, and side effects.
4. Give each node a narrow typed contract. Validate data at graph boundaries rather than passing unstructured dictionaries through the whole workflow.
5. Make routing predicates pure and explicit. Log the values that caused a branch to be selected.
6. Keep side effects idempotent or checkpointed so retries do not duplicate files, requests, or charges.
7. Represent human approval as a persisted boundary between graph runs unless the pinned Strands version provides a tested pause/resume contract.

## Version-Sensitive Behavior

Do not assume join or conditional-edge semantics from memory. Confirm them against the pinned version with a minimal executable test, especially when a node has multiple incoming edges or conditional predecessors.

## Testing

- Use fake models and deterministic fixtures; normal tests must not call external providers.
- Cover the happy path, every conditional route, invalid structured output, retry exhaustion, and skipped nodes.
- Assert node order only where order is part of the contract; parallel branches should be tested by outcome.
- Run the narrow graph integration test after each topology change.

## Done When

The graph is understandable from its topology, every route is tested, deterministic work stays outside model calls, and failures produce a resumable state or a clear terminal report.