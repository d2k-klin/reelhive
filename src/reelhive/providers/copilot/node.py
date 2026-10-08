from __future__ import annotations

import asyncio
from typing import Any

from pydantic import ValidationError
from strands.types.event_loop import Usage

from reelhive.core.context import RunContext
from reelhive.nodes.base import AgentNode, FunctionNode, _no_usage, load_prompt
from reelhive.providers.factory import ProviderError, model_id


def deny_permission(request: Any, invocation: Any) -> Any:
    from copilot.generated.rpc import PermissionDecisionUserNotAvailable

    return PermissionDecisionUserNotAvailable()


class CopilotAgentNode(FunctionNode):
    """Same graph contract, with Copilot's runtime in place of a Strands model."""

    name = "copilot"

    def __init__(self, node: AgentNode) -> None:
        self.node = node
        super().__init__()

    async def execute(self, ctx: RunContext) -> Usage:
        try:
            from copilot import CopilotClient
            from copilot.tools import Tool, ToolResult
        except ImportError as e:
            raise ProviderError("Install the Copilot extra: uv sync --extra copilot") from e

        submitted = None
        errors = []
        usage = _no_usage()
        tool_name = f"submit_{self.node.name}"

        def submit(invocation: Any) -> Any:
            nonlocal submitted
            try:
                submitted = self.node.output.model_validate(invocation.arguments)
            except ValidationError as e:
                errors.append(str(e))
                return ToolResult(text_result_for_llm=str(e), result_type="failure")
            return ToolResult(text_result_for_llm="Accepted")

        def stream(event: Any) -> None:
            kind = getattr(event.type, "value", event.type)
            if kind == "assistant.message_delta":
                ctx.events.emit("agent.text", node=self.node.name, text=event.data.delta_content or "")
            elif kind == "assistant.usage":
                usage["inputTokens"] += int(event.data.input_tokens or 0)
                usage["outputTokens"] += int(event.data.output_tokens or 0)
                usage["totalTokens"] = usage["inputTokens"] + usage["outputTokens"]

        # Only our side-effect-free submit tool bypasses the deny-all permission handler.
        tool = Tool(
            name=tool_name,
            description="Submit the validated result",
            handler=submit,
            parameters=self.node.output.model_json_schema(),
            skip_permission=True,
            is_terminal=True,
        )
        client = CopilotClient()
        try:
            await client.start()
            session = await client.create_session(
                model=model_id(ctx.config, "copilot", self.node.tier),
                tools=[tool],
                available_tools=[tool_name],
                on_permission_request=deny_permission,
                system_message={"mode": "replace", "content": load_prompt(self.node.prompt)},
                streaming=True,
                on_event=stream,
                working_directory=str(ctx.run_dir.resolve()),
                enable_config_discovery=False,
                skip_custom_instructions=True,
                enable_file_hooks=False,
                enable_host_git_operations=False,
                enable_skills=False,
                enable_session_store=False,
                mcp_servers={},
            )
            try:
                await session.send_and_wait(self.node.build_prompt(ctx) + f"\nCall {tool_name} to finish.", timeout=180)
                if submitted is None:
                    ctx.events.emit("node.task", node=self.node.name, task="Repairing invalid structured output")
                    await session.send_and_wait(
                        load_prompt("fixer") + f"\nRepair output for {tool_name}. Errors: {errors}", timeout=180
                    )
                if submitted is None:
                    raise ProviderError(f"Copilot {self.node.name} did not submit valid output: {errors}")
                await asyncio.to_thread(self.node.apply, ctx, submitted)
            finally:
                await session.disconnect()
        finally:
            await client.stop()
        return usage


async def list_models() -> list[str]:
    from copilot import CopilotClient

    client = CopilotClient()
    try:
        await client.start()
        return [model.id for model in await client.list_models()]
    finally:
        await client.stop()


async def auth_status() -> bool:
    from copilot import CopilotClient

    client = CopilotClient()
    try:
        await client.start()
        return bool((await client.get_auth_status()).isAuthenticated)
    finally:
        await client.stop()
