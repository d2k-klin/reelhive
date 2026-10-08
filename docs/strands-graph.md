# Learning notes: Strands Graph

ReelHive is meant to be a readable reference for [Strands Agents](https://strandsagents.com) graphs: parallel branches, conditional edges, and custom nodes that never call an LLM. These notes are what we learned building it, verified against strands-agents 1.59.

## Every node is a `MultiAgentBase`

A graph node can be a Strands `Agent` or any `MultiAgentBase`. ReelHive uses `MultiAgentBase` for everything (`nodes/base.py`), so that agent and non-agent nodes share one contract and one set of events:

```python
class FunctionNode(MultiAgentBase):
    name: ClassVar[str]

    def run(self, ctx: RunContext) -> None: ...  # deterministic work, runs in a worker thread

    async def invoke_async(self, task, invocation_state=None, **kwargs) -> MultiAgentResult:
        ctx = invocation_state["ctx"]
        ctx.events.emit("node.started", node=self.name)
        usage = await self.execute(ctx)  # asyncio.to_thread(self.run, ctx)
        ctx.events.emit("node.finished", ...)
        return MultiAgentResult(status=Status.COMPLETED, accumulated_usage=usage)
```

`AgentNode` overrides `execute` to build a prompt from the run, call `Agent.invoke_async(prompt, structured_output_model=...)`, and apply the validated result. Blocking work (TTS, Playwright, ffmpeg) goes through `asyncio.to_thread`, so parallel branches really overlap.

## Pass state through `invocation_state`, not node text

By default a node's input is the text output of the nodes before it. That's fine for chat-style agents but wrong for a pipeline whose data is a typed spec. ReelHive passes one `RunContext` as `invocation_state={"ctx": ctx}`; Strands forwards it to every `MultiAgentBase` node and to edge conditions. Nodes read and write typed fields (`ctx.script`, `ctx.spec`, `ctx.narrated`), and each field has exactly one writer per phase, so parallel branches don't race.

## Joins are OR, not AND

The most important finding: **a node becomes ready as soon as any one incoming edge is satisfied** (`_is_node_ready_with_conditions`). Two consequences:

1. **Fan-in needs a condition.** `timing` must wait for `visuals`, `narrate` and `music`. Each of those edges carries the same condition:

   ```python
   def all_branches_done(state: GraphState) -> bool:
       return {"visuals", "narrate", "music"} <= {n.node_id for n in state.completed_nodes}
   ```

   Without it, `timing` would start after whichever branch finished first.

2. **Alternatives share one node.** `render` has two conditional incoming edges, `critic → render` (passed) and `recheck → render` (recheck passed). Only one can ever be true, so one `render` node is enough. There's no need for a second node sharing the executor.

## Conditions can read the run

A condition with an `invocation_state` keyword parameter receives the invocation state (Strands detects this by parameter name):

```python
def critic_passed(state: GraphState, *, invocation_state: dict[str, Any], **_: Any) -> bool:
    return bool(invocation_state["ctx"].critic_passed)
```

## Ending without a dead end

If `recheck` fails, neither of its outgoing conditions is true, so no node becomes ready and the graph completes normally. The service compares `result.execution_order` with the node list, emits `node.skipped` for whatever didn't run, and reports the failures. A graph that "ends early" is just one with no ready nodes left.

## Approvals sit between graphs

A graph runs to completion, so a human pause can't live inside one. The draft graph (`brief → script`) ends, the service saves `script.json` and `status.json`, and `reelhive approve` later starts the production graph on the edited script. The two graphs share a `RunContext` shape, not a process.

## Limits

`set_max_node_executions(len(NODES))` makes runaway loops impossible. The production graph has no cycle (the `fix` path runs at most once by design), so the limit is a guard, not a control-flow tool.

## Structured output and repair

`Agent.invoke_async(..., structured_output_model=Model)` registers a tool built from the Pydantic model. Validation errors go back to the model as a tool error, so it retries within the same call. ReelHive adds one more explicit repair turn if that still fails, and then fails the node. Template character limits are enforced in a `model_validator`, so a headline that's too long is fixed by the model, not truncated by us.
