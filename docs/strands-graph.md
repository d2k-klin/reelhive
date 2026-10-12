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

## Output models built per run

Sometimes the valid answers depend on the run. The `sound` node may only choose a moment the renderer reported and an effect from the library, and the `publish` node must write one block for each platform the user picked. Both build their output model in `execute`, before calling the agent: closed sets become `Literal` fields, and the rules (budget, spacing, levels under the voice, each platform's limits) become `model_validator`s. Strands registers the model as the structured-output tool, so a plan that breaks a rule comes back to the model as a tool error and is repaired within the same call. Nothing is clamped or truncated afterwards, and the Copilot path gets the same model, because it reads `node.output` from the instance.

## Branches that must not fail together

The publishing graph fans out from `ready` to one `post_<platform>` node per platform. They are independent, so each one catches its own failure, records it in the job, and completes. A raised exception would fail the whole graph and stop the others mid-upload. Each node saves the job (`publish/job.json`) the moment its post lands, so a crash never forgets a live post, and a node whose platform is already published returns at once. Retrying is safe: run the same graph again.

## A gate on both sides of a human

Publishing is two graphs with a person in between: `ready -> publish` drafts, the user approves, and `ready -> post_*` posts. `ready` runs in both graphs, because accounts and settings can change while the draft waits for approval. It's the same pattern as `critic` and `review`: the cheapest deterministic check runs first, and a failed gate ends the graph with no node ready. No model is called and nothing is sent.
