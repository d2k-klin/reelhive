"""AG-UI endpoint for M6 quick actions (plan §3.10, UI plan §16).

CopilotKit in the Script and Scenes screens talks to this endpoint with the AG-UI protocol. The run
streams one `propose_suggestions` tool call, which CopilotKit renders as buttons (generative UI).

The suggestions come from `Service.suggest`, not from a free-running agent loop, so they are validated
(3-4, distinct, bounded), cached per version of the beat or scene, and logged as `suggestion.offered`
exactly as for the CLI. The endpoint sits under /api, behind the launch token, Host and Origin checks.
Applying a suggestion is a separate call to the existing regenerate routes; this endpoint never edits a run.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Literal

from ag_ui.core import (
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
)
from ag_ui.encoder import EventEncoder
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ValidationError

from reelhive.core.workspace import Workspace
from reelhive.providers.factory import ProviderError

TOOL = "propose_suggestions"


class SuggestState(BaseModel):
    """The only state the browser shares with the agent: which beat or scene is selected."""

    run_id: str
    target: Literal["beat", "scene"]
    index: int = Field(ge=1, le=99)
    fresh: bool = False  # "More ideas"


def mount(app: FastAPI, ws: Workspace) -> None:
    @app.post("/api/agui/suggest", include_in_schema=False)
    async def agui_suggest(request: Request) -> StreamingResponse:
        run = RunAgentInput.model_validate(await request.json())
        encoder = EventEncoder(accept=request.headers.get("accept", "text/event-stream"))

        async def stream():
            yield encoder.encode(RunStartedEvent(thread_id=run.thread_id, run_id=run.run_id))
            # After the browser shows the buttons it may report the tool result back; there is nothing more to say.
            if run.messages and run.messages[-1].role == "tool":
                yield encoder.encode(RunFinishedEvent(thread_id=run.thread_id, run_id=run.run_id))
                return
            try:
                state = SuggestState.model_validate(run.state or {})
                result = await asyncio.to_thread(ws.suggest, state.run_id, state.target, state.index, state.fresh)
            except (ValidationError, ValueError, FileNotFoundError, ProviderError) as error:
                yield encoder.encode(RunErrorEvent(message=str(error)))
                return
            call = str(uuid.uuid4())
            yield encoder.encode(
                ToolCallStartEvent(tool_call_id=call, tool_call_name=TOOL, parent_message_id=str(uuid.uuid4()))
            )
            yield encoder.encode(ToolCallArgsEvent(tool_call_id=call, delta=json.dumps(result.model_dump())))
            yield encoder.encode(ToolCallEndEvent(tool_call_id=call))
            yield encoder.encode(RunFinishedEvent(thread_id=run.thread_id, run_id=run.run_id))

        return StreamingResponse(stream(), media_type=encoder.get_content_type())
