"""Local application operations shared by the CLI and HTTP interface."""

from __future__ import annotations

import asyncio
import io
import json
import os
import shutil
import subprocess
import sys
import threading
import uuid
import zipfile
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

import yaml
from PIL import Image
from pydantic import BaseModel

from reelhive.config import Config
from reelhive.core.events import EventBus
from reelhive.core.service import Service
from reelhive.schemas.brief import Brief, Images, Screenshots
from reelhive.schemas.scene_spec import SceneSpec
from reelhive.schemas.script import Script

BUSY = {"drafting", "producing", "queued", "regenerating", "capturing"}
DOWNLOADS = {"video.mp4", "brief.yaml", "script.json", "spec.json", "run.log.jsonl", "script.approved.json"}


class RunView(BaseModel):
    id: str
    status: str
    brief: Brief | None = None
    script: Script | None = None
    spec: SceneSpec | None = None
    provider: str = "claude"
    report: list[str] = []
    queue_position: int | None = None
    video: bool = False


class Workspace:
    def __init__(
        self, config: Config, config_path: Path | None = None, service_factory: Callable[[Config], Service] = Service
    ):
        self.config = config
        self.config_path = config_path or Path("config.yaml")
        self.root = config.runs_dir.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.factory = service_factory
        self.pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="reelhive")
        self.production = threading.Lock()
        self.lock = threading.RLock()
        self.jobs: dict[str, Future] = {}
        self.queue: list[str] = []
        self.logins: dict[str, dict[str, Any]] = {}
        for path in self.root.iterdir():
            status = path / "status.json"
            if path.is_dir() and status.is_file() and json.loads(status.read_text()).get("status") in BUSY:
                status.write_text(json.dumps({"status": "interrupted"}))
                (path / ".production.lock").unlink(missing_ok=True)

    @staticmethod
    def _write_status(path: Path, status: str, report: list[str] | None = None) -> None:
        value: dict[str, Any] = {"status": status}
        if report:
            value["report"] = report
        temporary = path / f".status.{uuid.uuid4().hex}.tmp"
        temporary.write_text(json.dumps(value))
        temporary.replace(path / "status.json")

    def path(self, run_id: str) -> Path:
        if not run_id or Path(run_id).name != run_id or run_id.startswith("."):
            raise ValueError("invalid run id")
        path = (self.root / run_id).resolve()
        if not path.is_relative_to(self.root) or not path.is_dir():
            raise FileNotFoundError("run not found")
        return path

    def service(self, run_id: str) -> Service:
        path = self.path(run_id)
        config = Config.model_validate_json((path / "config.json").read_text())
        return self.factory(config)

    def details(self, run_id: str) -> RunView:
        path = self.path(run_id)
        state = json.loads((path / "status.json").read_text())
        brief = Brief.model_validate(yaml.safe_load((path / "brief.yaml").read_text()))

        def read(name, model):
            file = path / name
            return model.model_validate_json(file.read_text()) if file.exists() else None

        config = Config.model_validate_json((path / "config.json").read_text())
        with self.lock:
            position = self.queue.index(run_id) + 1 if run_id in self.queue else None
        return RunView(
            id=run_id,
            status=state["status"],
            brief=brief,
            script=read("script.json", Script),
            spec=read("spec.json", SceneSpec),
            provider=config.provider,
            report=state.get("report", []),
            queue_position=position,
            video=(path / "video.mp4").exists(),
        )

    def list_runs(self) -> list[RunView]:
        runs = []
        for path in sorted(self.root.iterdir(), reverse=True):
            if path.is_dir() and (path / "status.json").is_file():
                try:
                    runs.append(self.details(path.name))
                except (ValueError, OSError):
                    continue
        return runs

    def create(self, brief: Brief, start: bool = True) -> RunView:
        # Editing/upload folders do not initialize providers or make model calls.
        run_id = uuid.uuid4().hex
        path = self.root / run_id
        path.mkdir()
        (path / "brief.yaml").write_text(yaml.safe_dump(brief.model_dump(mode="json"), sort_keys=False))
        (path / "config.json").write_text(self.config.model_dump_json(indent=2))
        self._write_status(path, "editing")
        if start:
            self.start(run_id, brief)
        return self.details(run_id)

    def submit(
        self,
        run_id: str,
        operation: Callable[[], Any],
        *,
        production: bool = True,
        before_submit: Callable[[], Any] | None = None,
    ) -> None:
        path = self.path(run_id)
        with self.lock:
            if run_id in self.jobs and not self.jobs[run_id].done():
                raise ValueError("run already has an active operation")
            if before_submit:
                before_submit()
            if production:
                self.queue.append(run_id)
                self._write_status(path, "queued")
                EventBus(path / "run.log.jsonl").emit("run.queued", position=len(self.queue))

            def work():
                acquired = False
                try:
                    if production:
                        while not self.production.acquire(timeout=0.2):
                            if (path / "cancel.requested").exists():
                                return
                        acquired = True
                        with self.lock:
                            self.queue.remove(run_id)
                    if not (path / "cancel.requested").exists():
                        operation()
                except Exception as error:
                    self._write_status(path, "failed", [str(error)])
                    EventBus(path / "run.log.jsonl").emit("run.finished", status="failed", report=[str(error)])
                finally:
                    with self.lock:
                        if run_id in self.queue:
                            self.queue.remove(run_id)
                    if acquired:
                        self.production.release()
                    if (path / "cancel.requested").exists():
                        self._write_status(path, "cancelled")

            self.jobs[run_id] = self.pool.submit(work)

    def start(self, run_id: str, brief: Brief) -> None:
        path = self.path(run_id)
        Service.require_status(path, {"editing"})
        (path / "brief.yaml").write_text(yaml.safe_dump(brief.model_dump(mode="json"), sort_keys=False))
        self._write_status(path, "drafting")

        def draft():
            from reelhive.graphs.draft import build_draft_graph

            svc = self.service(run_id)
            ctx = svc.load(path)
            asyncio.run(build_draft_graph().invoke_async("Write the script", {"ctx": ctx}))
            if brief.level == "small":
                # Enqueue production only after releasing this draft job's slot.
                self._write_status(path, "awaiting_script")
                with self.lock:
                    self.jobs.pop(run_id, None)
                self.approve_script(run_id, ctx.script)
            else:
                svc._status(ctx, "awaiting_script")
                ctx.events.emit("run.paused", status="awaiting_script")

        self.submit(run_id, draft, production=False)

    def approve_script(self, run_id: str, script: Script) -> None:
        path = self.path(run_id)
        svc = self.service(run_id)

        def approve():
            self._write_status(path, "awaiting_script")
            svc.approve(path)

        self.submit(run_id, approve, before_submit=lambda: svc.save_script(path, script))

    def approve_scenes(self, run_id: str) -> None:
        path = self.path(run_id)
        Service.require_status(path, {"awaiting_scenes", "stopped"})

        def approve():
            self._write_status(path, "awaiting_scenes")
            self.service(run_id).approve_scenes(path)

        self.submit(run_id, approve)

    def regenerate_script(self, run_id: str, note: str, suggestion: str | None = None, beat: int | None = None) -> None:
        path = self.path(run_id)
        Service.require_status(path, {"awaiting_script"})

        def regenerate():
            self._write_status(path, "awaiting_script")
            self.service(run_id).regenerate_script(path, note, suggestion, beat)
            self._write_status(path, "awaiting_script")

        self.submit(
            run_id,
            regenerate,
            production=False,
            before_submit=lambda: self._write_status(path, "regenerating"),
        )

    def edit_spec(self, run_id: str, spec: SceneSpec) -> None:
        path = self.path(run_id)
        Service.require_status(path, {"awaiting_scenes", "stopped", "done"})

        def edit():
            self._write_status(path, "awaiting_scenes")
            self.service(run_id).save_spec(path, spec)

        self.submit(run_id, edit)

    def regenerate_scene(self, run_id: str, index: int, note: str, suggestion: str | None = None) -> None:
        path = self.path(run_id)
        Service.require_status(path, {"awaiting_scenes", "stopped", "done"})

        def regenerate():
            self._write_status(path, "awaiting_scenes")
            self.service(run_id).regenerate_scene(path, index, note, suggestion)

        self.submit(run_id, regenerate)

    def undo_script(self, run_id: str) -> None:
        path = self.path(run_id)
        self.service(run_id).undo_script(path)

    def undo_scene(self, run_id: str, index: int) -> None:
        path = self.path(run_id)
        Service.require_status(path, {"awaiting_scenes", "stopped", "done"})

        def undo():
            self._write_status(path, "awaiting_scenes")
            self.service(run_id).undo_scene(path, index)

        self.submit(run_id, undo)

    def suggest(self, run_id: str, target: str, index: int, fresh: bool = False):
        path = self.path(run_id)
        return self.service(run_id).suggest(path, target, index, fresh=fresh)

    def cancel(self, run_id: str) -> None:
        self.service(run_id).cancel(self.path(run_id))
        EventBus(self.path(run_id) / "run.log.jsonl").emit("run.cancelled", status="cancelling")

    def resume(self, run_id: str) -> None:
        path = self.path(run_id)
        previous = Service.require_status(path, {"interrupted", "failed", "cancelled"})

        def resume():
            self._write_status(path, previous)
            self.service(run_id).resume(path)

        (path / "cancel.requested").unlink(missing_ok=True)
        self.submit(run_id, resume)

    def events(self, run_id: str, after: int = 0):
        file = self.path(run_id) / "run.log.jsonl"
        if not file.exists():
            return []
        # An append may be in progress; consume complete lines only.
        lines = file.read_text().splitlines(keepends=True)
        from reelhive.core.events import Event

        return [
            Event(**{**json.loads(line), "id": i})
            for i, line in enumerate(lines, 1)
            if i > after and line.endswith("\n")
        ]

    def file(self, run_id: str, name: str) -> Path:
        root = self.path(run_id)
        path = (root / name).resolve()
        media = Path(name).parts[0] in {"visuals", "audio", "uploads"} if Path(name).parts else False
        if (
            not path.is_relative_to(root)
            or not path.is_file()
            or not (name in DOWNLOADS or media and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".wav"})
        ):
            raise FileNotFoundError("artifact not available")
        return path

    def bundle(self, run_id: str) -> bytes:
        root = self.path(run_id)
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in root.rglob("*"):
                if path.is_file():
                    name = path.relative_to(root).as_posix()
                    try:
                        safe = self.file(run_id, name)
                    except (FileNotFoundError, ValueError):
                        continue
                    archive.write(safe, name)
        return output.getvalue()

    def upload(self, run_id: str, data: bytes, filename: str, caption: str = "", logo: bool = False) -> dict:
        path = self.path(run_id)
        Service.require_status(path, {"editing", "awaiting_script", "awaiting_scenes"})
        if len(data) > 10 * 1024 * 1024:
            raise ValueError("image exceeds the 10 MB limit")
        if Path(filename).suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            raise ValueError("only PNG, JPEG and WebP images are accepted")
        with Image.open(io.BytesIO(data)) as image:
            if image.format not in {"PNG", "JPEG", "WEBP"} or image.width * image.height > 30_000_000:
                raise ValueError("unsupported image or more than 30 megapixels")
            output = path / "uploads" / f"{uuid.uuid4().hex}.png"
            output.parent.mkdir(exist_ok=True)
            image.convert("RGBA").save(output, format="PNG")
        brief = Brief.model_validate(yaml.safe_load((path / "brief.yaml").read_text()))
        if logo:
            brief.brand.logo = str(output)
        else:
            brief.visuals.images = Images(dir=str(output.parent))
            captions_path = output.parent / "captions.yaml"
            captions = yaml.safe_load(captions_path.read_text()) if captions_path.exists() else {}
            captions[output.name] = caption or Path(filename).stem
            captions_path.write_text(yaml.safe_dump(captions))
        (path / "brief.yaml").write_text(yaml.safe_dump(brief.model_dump(mode="json"), sort_keys=False))
        return {"name": output.name, "file": str(output), "caption": caption, "brief": brief.model_dump(mode="json")}

    def test_capture(self, run_id: str, options: Screenshots, format: str) -> list[str]:
        from reelhive.visuals.capture import capture, discover

        root = self.path(run_id)
        result = []
        for index, page in enumerate(discover(options, format)):
            file = root / "visuals" / f"preview_{index}.png"
            capture(options, format, page["route"], file)
            result.append(file.relative_to(root).as_posix())
        return result

    def login_start(self, run_id: str, url: str) -> str:
        from reelhive.visuals.login import login

        root = self.path(run_id)
        key = uuid.uuid4().hex
        finish = threading.Event()
        self.logins[key] = {"status": "waiting", "finish": finish, "run_id": run_id}

        def job():
            try:
                output = root / "private" / "auth.json"
                login(url, output, confirm=lambda _: finish.wait(timeout=600))
                self.logins[key]["status"] = "signed_in"
                self.logins[key]["file"] = str(output)
            except Exception as error:
                self.logins[key].update(status="failed", error=str(error))

        self.pool.submit(job)
        return key

    def login_status(self, key: str, finish: bool = False) -> dict:
        state = self.logins[key]
        if finish:
            state["finish"].set()
        return {k: v for k, v in state.items() if k != "finish"}

    def delete(self, run_id: str) -> None:
        if run_id in self.jobs and not self.jobs[run_id].done():
            raise ValueError("cancel the run and wait for it to stop before deleting")
        shutil.rmtree(self.path(run_id))

    def reveal(self, run_id: str) -> None:
        path = str(self.path(run_id))
        if sys.platform == "win32":
            os.startfile(path)
        else:
            subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", path])

    def close(self):
        for run_id, job in list(self.jobs.items()):
            if not job.done():
                (self.path(run_id) / "cancel.requested").touch()
        for state in self.logins.values():
            state["finish"].set()
        self.pool.shutdown(wait=True, cancel_futures=True)
