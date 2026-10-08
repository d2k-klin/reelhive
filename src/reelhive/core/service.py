"""Starts runs and drives the graphs. The CLI (and the M3 UI) are thin layers over this."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from reelhive.config import Config
from reelhive.core.context import RunCancelled, RunContext
from reelhive.core.events import Event, EventBus
from reelhive.graphs.draft import build_draft_graph
from reelhive.graphs.production import NODES as PRODUCTION_NODES
from reelhive.graphs.production import build_production_graph
from reelhive.levels import LEVELS
from reelhive.schemas.brief import Brief
from reelhive.schemas.scene_spec import SceneSpec
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
        *,
        spec_only: bool = False,
        image_generator: Any = None,
    ) -> None:
        self.config = config
        self._models = models
        self._tts = tts
        self._renderer = renderer
        self.spec_only = spec_only
        self.image_generator = image_generator

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
            spec_only=self.spec_only,
            image_generator=self.image_generator,
        )

    @staticmethod
    def _status(ctx: RunContext, status: str, report: list[str] | None = None) -> None:
        temporary = ctx.path("status.tmp")
        data: dict[str, object] = {"status": status}
        if report:
            data["report"] = report
        temporary.write_text(json.dumps(data))
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
            stage = (
                "prepare"
                if ctx.brief.level == "high" and ctx.stage != "finish"
                else "finish"
                if ctx.stage == "finish"
                else "all"
            )
            ctx.stage = stage
            ctx.checkpoint()
            result = await build_production_graph(stage).invoke_async(task, state)
            if stage == "prepare":
                self._status(ctx, "awaiting_scenes")
                ctx.events.emit("run.paused", status="awaiting_scenes")
                return RunResult(ctx.run_dir, "awaiting_scenes")
        except RunCancelled:
            self._status(ctx, "cancelled")
            ctx.events.emit("run.cancelled", status="cancelled")
            return RunResult(ctx.run_dir, "cancelled")
        except Exception as e:
            report = [f"{type(e).__name__}: {e}"]
            self._status(ctx, "failed", report)
            ctx.events.emit("run.finished", status="failed", report=report)
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
        if ctx.spec_only and "render" in ran:
            ctx.events.emit("run.finished", status="done", spec=str(ctx.path("spec.json")))
            self._status(ctx, "done")
            return RunResult(ctx.run_dir, "done")
        ctx.events.emit("run.finished", status="stopped", report=ctx.failures)
        self._status(ctx, "stopped", ctx.failures)
        return RunResult(ctx.run_dir, "stopped", report=ctx.failures)

    def run(self, brief: Brief, on_event: Callable[[Event], None] | None = None) -> RunResult:
        return asyncio.run(self.run_async(self.new_run(brief, on_event)))

    def approve(self, run_dir: Path, on_event: Callable[[Event], None] | None = None) -> RunResult:
        run_dir = run_dir.resolve()
        # Exclusive marker prevents two terminals from producing the same run concurrently.
        lock = run_dir / ".production.lock"
        try:
            with lock.open("x"):
                pass
        except FileExistsError as e:
            raise ValueError(f"run is already being produced; if no other process is, delete {lock}") from e
        try:
            if json.loads((run_dir / "status.json").read_text())["status"] != "awaiting_script":
                raise ValueError("run is not awaiting script approval")
            ctx = self.load(run_dir, on_event)
            ctx.script = Script.model_validate_json((run_dir / "script.json").read_text())
            script = ctx.script
            ctx.path("script.approved.json").write_text(script.model_dump_json(indent=2))
            ctx.events.emit("script.approved", beats=len(script.beats))
            return asyncio.run(self.run_async(ctx, approved=True))
        finally:
            lock.unlink()

    def suggest(self, run_dir: Path, kind: str, index: int, on_event: Callable[[Event], None] | None = None) -> Any:
        """3-4 quick-action suggestions for one beat or scene of a run (M6). Read-only; cached per version."""
        from reelhive.agents.suggester import suggest
        from reelhive.providers.factory import ProviderError, build_model
        from reelhive.schemas.scene_spec import SceneSpec

        run_dir = run_dir.resolve()
        brief = Brief.model_validate(yaml.safe_load((run_dir / "brief.yaml").read_text()))
        script = Script.model_validate_json((run_dir / "script.json").read_text())
        spec_path = run_dir / "spec.json"
        spec = SceneSpec.model_validate_json(spec_path.read_text()) if spec_path.exists() else None
        if self._models and "fast" in self._models:
            model = self._models["fast"]
        elif self.config.provider == "copilot":
            # ponytail: first version runs on Strands providers (plan §3.10); Copilot is a follow-up.
            raise ProviderError("suggestions run on Claude, Bedrock, OpenAI or Ollama; Copilot is a follow-up")
        else:
            model = build_model(self.config, self.config.provider, "fast")
        events = EventBus(run_dir / "run.log.jsonl")
        if on_event:
            events.subscribe(on_event)
        return asyncio.run(suggest(model, run_dir, kind, index, brief, script, spec, events))  # type: ignore[arg-type]

    def load(self, run_dir: Path, on_event: Callable[[Event], None] | None = None) -> RunContext:
        self._dependencies()
        brief = Brief.model_validate(yaml.safe_load((run_dir / "brief.yaml").read_text()))
        ctx = self._context(run_dir.resolve(), brief, on_event)
        if (run_dir / "checkpoint.json").exists():
            ctx.restore()
        return ctx

    def save_script(self, run_dir: Path, script: Script) -> None:
        self.require_status(run_dir, {"awaiting_script"})
        temporary = run_dir / "script.tmp"
        temporary.write_text(script.model_dump_json(indent=2))
        temporary.replace(run_dir / "script.json")

    @staticmethod
    def require_status(run_dir: Path, allowed: set[str]) -> str:
        status = json.loads((run_dir / "status.json").read_text())["status"]
        if status not in allowed:
            raise ValueError(f"run is {status}; expected {', '.join(sorted(allowed))}")
        return status

    def regenerate_script(self, run_dir: Path, note: str = "") -> RunResult:
        from reelhive.agents.script_writer import ScriptWriterNode

        self.require_status(run_dir, {"awaiting_script"})
        ctx = self.load(run_dir)
        ctx.note = note
        ctx.completed.discard("script")
        asyncio.run(ScriptWriterNode().invoke_async("Rewrite script", {"ctx": ctx}))
        return RunResult(run_dir, "awaiting_script")

    def refresh_scenes(self, ctx: RunContext) -> None:
        from reelhive.nodes.narrate_node import narrate
        from reelhive.nodes.timing_node import apply_timing
        from reelhive.visuals.resolver import resolve

        assert ctx.spec
        for scene in ctx.spec.scenes:
            if (
                ctx.narrated.get(scene.index, ("",))[0] != scene.narration
                or ctx.voiced.get(scene.index) != (scene.voice_override or ctx.brief.voice).model_dump()
            ):
                narrate(ctx, scene.index, scene.narration)
        resolve(ctx)
        apply_timing(ctx.spec, ctx.narrated, ctx.brief)
        ctx.completed.difference_update({"critic", "fix", "recheck", "render"})
        ctx.critic_passed = ctx.recheck_passed = False
        ctx.checkpoint()

    def save_spec(self, run_dir: Path, spec: SceneSpec) -> RunResult:
        self.require_status(run_dir, {"awaiting_scenes", "stopped", "done"})
        ctx = self.load(run_dir)
        assert ctx.spec
        if len(spec.scenes) != len(ctx.spec.scenes) or [s.index for s in spec.scenes] != list(
            range(1, len(spec.scenes) + 1)
        ):
            raise ValueError("scene edits must preserve scene count and consecutive indices")
        for scene, old in zip(spec.scenes, ctx.spec.scenes, strict=True):
            # Asset paths and audio come from the resolver, never the editor.
            same_visual = scene.visual_request == old.visual_request
            scene.visual = old.visual if same_visual else None
            scene.audio = old.audio
            scene.image_approved = scene.image_approved if same_visual else False
        ctx.spec.scenes = spec.scenes
        ctx.spec.music_volume = spec.music_volume
        self.refresh_scenes(ctx)
        self._status(ctx, "awaiting_scenes")
        ctx.events.emit("spec.edited", scenes=[s.index for s in spec.scenes])
        return RunResult(run_dir, "awaiting_scenes")

    def approve_scenes(self, run_dir: Path, on_event: Callable[[Event], None] | None = None) -> RunResult:
        self.require_status(run_dir, {"awaiting_scenes", "stopped"})
        ctx = self.load(run_dir, on_event)
        assert ctx.spec
        ctx.spec = SceneSpec.model_validate_json((run_dir / "spec.json").read_text())
        if any(s.visual and not s.image_approved for s in ctx.spec.scenes):
            raise ValueError("approve every scene image before rendering")
        ctx.stage = "finish"
        ctx.checkpoint()
        return asyncio.run(self.run_async(ctx, approved=True))

    def regenerate_scene(self, run_dir: Path, index: int, note: str = "") -> RunResult:
        from reelhive.agents.plan import ScenePlan, brief_block
        from reelhive.agents.scene_planner import ScenePlannerNode

        self.require_status(run_dir, {"awaiting_scenes", "stopped", "done"})
        ctx = self.load(run_dir)
        assert ctx.spec
        if not 1 <= index <= len(ctx.spec.scenes):
            raise ValueError("scene index is out of range")
        old = ctx.spec.scenes[index - 1]

        class Regenerate(ScenePlannerNode):
            def build_prompt(self, ctx):
                return (
                    f"{brief_block(ctx.brief)}\nRegenerate exactly this one scene: {old.model_dump_json()}"
                    f"\nNote: {note}. You may rewrite narration. Return a plan containing exactly one scene."
                )

            def apply(self, ctx, out: ScenePlan):
                if len(out.scenes) != 1:
                    raise ValueError("regeneration must return exactly one scene")
                result = out.scenes[0].to_scene(index, out.scenes[0].narration or old.narration)
                result.voice_override, result.duration_override = old.voice_override, old.duration_override
                ctx.spec.scenes[index - 1] = result

        # Use the agent executor without the planner's catalog/spec initialization.
        from reelhive.nodes.base import AgentNode

        asyncio.run(AgentNode.execute(Regenerate(), ctx))
        self.refresh_scenes(ctx)
        self._status(ctx, "awaiting_scenes")
        ctx.events.emit("spec.edited", scenes=[index], note=note)
        return RunResult(run_dir, "awaiting_scenes")

    def cancel(self, run_dir: Path) -> None:
        (run_dir / "cancel.requested").touch()

    def resume(self, run_dir: Path, on_event: Callable[[Event], None] | None = None) -> RunResult:
        self.require_status(run_dir, {"interrupted", "failed", "cancelled"})
        (run_dir / "cancel.requested").unlink(missing_ok=True)
        ctx = self.load(run_dir, on_event)
        return asyncio.run(self.run_async(ctx, approved=ctx.stage != "draft"))
