"""Starts runs and drives the graphs. The CLI (and the M3 UI) are thin layers over this."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from reelhive.config import Config
from reelhive.core.context import RunContext
from reelhive.core.events import Event, EventBus
from reelhive.graphs.draft import build_draft_graph
from reelhive.graphs.production import NODES as PRODUCTION_NODES
from reelhive.graphs.production import build_production_graph
from reelhive.levels import LEVELS
from reelhive.schemas.brief import Brief
from reelhive.schemas.script import Script

if TYPE_CHECKING:
    from strands.models.model import Model

    from reelhive.audio.tts.base import TTS


@dataclass
class RunResult:
    run_dir: Path
    status: str  # "done" | "stopped"
    video: Path | None = None
    report: list[str] = field(default_factory=list)


def _slug(text: str) -> str:
    return "-".join(re.findall(r"[a-z0-9]+", text.lower())[:4]) or "run"


class Service:
    def __init__(
        self,
        config: Config,
        models: dict[str, Model] | None = None,
        tts: TTS | None = None,
        renderer: Callable[[Path, Path, Callable[[float], None]], None] | None = None,
    ) -> None:
        self.config = config
        self._models = models
        self._tts = tts
        self._renderer = renderer

    def _dependencies(self) -> None:
        if self._models is None:
            from reelhive.providers.factory import build_models

            self._models = build_models(self.config)
        if self._tts is None:
            from reelhive.audio.tts.kokoro import KokoroTTS

            self._tts = KokoroTTS()
        if self._renderer is None:
            from reelhive.render.bridge import render

            self._renderer = render

    def new_run(self, brief: Brief, on_event: Callable[[Event], None] | None = None) -> RunContext:
        self._dependencies()
        stamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S-%f")
        run_dir = self.config.runs_dir / f"{stamp}_{_slug(brief.storyline)}"
        run_dir.mkdir(parents=True, exist_ok=False)
        (run_dir / "config.json").write_text(self.config.model_dump_json(indent=2))
        return self._context(run_dir, brief, on_event)

    def _context(self, run_dir: Path, brief: Brief, on_event: Callable[[Event], None] | None) -> RunContext:
        assert self._models is not None and self._tts is not None and self._renderer is not None
        events = EventBus(run_dir / "run.log.jsonl")
        if on_event:
            events.subscribe(on_event)
        return RunContext(
            run_dir=run_dir,
            brief=brief,
            events=events,
            models=self._models,
            tts=self._tts,
            renderer=self._renderer,
            config=self.config,
        )

    @staticmethod
    def _status(ctx: RunContext, status: str) -> None:
        temporary = ctx.path("status.tmp")
        temporary.write_text(json.dumps({"status": status}))
        temporary.replace(ctx.path("status.json"))

    async def run_async(self, ctx: RunContext, *, approved: bool = False) -> RunResult:
        state = {"ctx": ctx}
        task = f"Make a {ctx.brief.duration}s video for: {ctx.brief.audience}"
        try:
            if not approved:
                self._status(ctx, "drafting")
                await build_draft_graph().invoke_async(task, state)
                if LEVELS[ctx.brief.level].approval_stops:
                    self._status(ctx, "awaiting_script")
                    ctx.events.emit("run.paused", status="awaiting_script", script=str(ctx.path("script.json")))
                    return RunResult(ctx.run_dir, "awaiting_script")
            self._status(ctx, "producing")
            result = await build_production_graph().invoke_async(task, state)
        except Exception as e:
            self._status(ctx, "failed")
            ctx.events.emit("run.finished", status="failed", report=[f"{type(e).__name__}: {e}"])
            raise
        ran = {n.node_id for n in result.execution_order}
        for node in PRODUCTION_NODES:
            if node not in ran:
                ctx.events.emit("node.skipped", node=node)
        if ctx.video:
            from reelhive.audio.mixer import probe

            info = probe(ctx.video)
            ctx.events.emit(
                "run.finished",
                status="done",
                video=str(ctx.video),
                duration=info["duration"],
                size=ctx.video.stat().st_size,
            )
            self._status(ctx, "done")
            return RunResult(ctx.run_dir, "done", video=ctx.video)
        ctx.events.emit("run.finished", status="stopped", report=ctx.failures)
        self._status(ctx, "stopped")
        return RunResult(ctx.run_dir, "stopped", report=ctx.failures)

    def run(self, brief: Brief, on_event: Callable[[Event], None] | None = None) -> RunResult:
        return asyncio.run(self.run_async(self.new_run(brief, on_event)))

    def approve(self, run_dir: Path, on_event: Callable[[Event], None] | None = None) -> RunResult:
        run_dir = run_dir.resolve()
        # Exclusive marker prevents two terminals from producing the same run concurrently.
        lock = run_dir / ".production.lock"
        with lock.open("x"):
            pass
        try:
            if json.loads((run_dir / "status.json").read_text())["status"] != "awaiting_script":
                raise ValueError("run is not awaiting script approval")
            brief = Brief.model_validate(yaml.safe_load((run_dir / "brief.yaml").read_text()))
            script = Script.model_validate_json((run_dir / "script.json").read_text())
            self._dependencies()
            ctx = self._context(run_dir, brief, on_event)
            ctx.script = script
            ctx.path("script.approved.json").write_text(script.model_dump_json(indent=2))
            ctx.events.emit("script.approved", beats=len(script.beats))
            return asyncio.run(self.run_async(ctx, approved=True))
        finally:
            lock.unlink()
