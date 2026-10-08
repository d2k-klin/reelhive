from __future__ import annotations

import asyncio
import json
import os
import secrets
import socket
import time
import webbrowser
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Annotated, Literal

import yaml
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError

from reelhive.config import REPO_ROOT, Config, load_config
from reelhive.core.workspace import RunView, Workspace
from reelhive.schemas.brief import Brief, Screenshots
from reelhive.schemas.scene_spec import SceneSpec
from reelhive.schemas.script import Script
from reelhive.schemas.voice import Voice
from reelhive.server.security import protect, validate_host


class CreateRun(BaseModel):
    brief: Brief
    start: bool = True


class Note(BaseModel):
    note: str = Field("", max_length=2000)


class YamlBrief(BaseModel):
    text: str = Field(max_length=100_000)


class CaptureRequest(BaseModel):
    run_id: str
    screenshots: Screenshots
    format: Literal["16:9", "9:16", "1:1"]


class LoginRequest(BaseModel):
    run_id: str
    url: str


def create_app(
    config: Config | None = None, *, token: str | None = None, workspace: Workspace | None = None
) -> FastAPI:
    ws = workspace or Workspace(config or load_config())
    launch_token = token or secrets.token_urlsafe(32)

    @asynccontextmanager
    async def lifespan(app):
        yield
        await asyncio.to_thread(ws.close)

    app = FastAPI(
        title="ReelHive local API", version="0.0.3", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan
    )
    app.state.workspace, app.state.token = ws, launch_token

    @app.middleware("http")
    async def secure(request: Request, call_next):
        return await protect(request, call_next, launch_token)

    @app.exception_handler(ValueError)
    async def bad_value(request, error):
        return JSONResponse({"detail": str(error)}, status_code=422)

    @app.exception_handler(FileNotFoundError)
    async def missing(request, error):
        return JSONResponse({"detail": "Run or artifact not found"}, status_code=404)

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "credit_disabled": os.getenv("REELHIVE_DISABLE_CREDIT", "").lower() in {"true", "1", "yes"},
        }

    @app.get("/api/schema")
    def schema():
        return app.openapi()

    @app.get("/api/doctor")
    def doctor():
        from reelhive.doctor import run_checks

        return [asdict(result) for result in run_checks(ws.config)]

    @app.get("/api/settings", response_model=Config)
    def settings():
        return ws.config

    @app.put("/api/settings", response_model=Config)
    def save_settings(config: Config):
        # Storage root changes take effect on the next launch so active runs never move.
        ws.config_path.write_text(yaml.safe_dump(config.model_dump(mode="json"), sort_keys=False))
        ws.config = config
        return config

    @app.get("/api/providers/status")
    def provider_status():
        from importlib.metadata import PackageNotFoundError, version

        versions = {}
        for package in ("reelhive", "strands-agents", "kokoro", "github-copilot-sdk"):
            try:
                versions[package] = version(package)
            except PackageNotFoundError:
                versions[package] = "not installed"
        versions["revideo"] = "0.11.0"
        return {
            "claude": bool(os.getenv("ANTHROPIC_API_KEY")),
            "openai": bool(os.getenv("OPENAI_API_KEY")),
            "copilot": bool(os.getenv("GH_TOKEN") or os.getenv("COPILOT_GITHUB_TOKEN")),
            "versions": versions,
            "runs_dir": str(ws.root),
            "disk_bytes": sum(p.stat().st_size for p in ws.root.rglob("*") if p.is_file() and not p.is_symlink()),
        }

    @app.get("/api/providers/{name}/models", response_model=list[str])
    def models(name: str):
        if name == "copilot":
            from reelhive.providers.copilot.node import list_models

            return asyncio.run(list_models())
        if name == "ollama":
            from ollama import Client

            return [model.model for model in Client(host=ws.config.ollama_host, timeout=5).list().models]
        return list(ws.config.models[name].model_dump().values()) if name in ws.config.models else []

    @app.post("/api/providers/{name}/test")
    def test_provider(name: str):
        from strands import Agent

        from reelhive.providers.factory import build_model

        started = time.monotonic()
        if name == "copilot":
            from reelhive.providers.copilot.node import auth_status

            ok = asyncio.run(auth_status())
            if not ok:
                raise ValueError("Copilot is not signed in")
        else:
            Agent(model=build_model(ws.config, name, "fast"), callback_handler=None)("Reply OK.")
        return {"ok": True, "seconds": round(time.monotonic() - started, 2)}

    @app.post("/api/voices/preview")
    def voice_preview(voice: Voice):
        import hashlib

        from reelhive.audio.tts.kokoro import KokoroTTS

        key = hashlib.sha256(voice.model_dump_json().encode()).hexdigest()
        path = ws.root / ".previews" / (key + ".wav")
        path.parent.mkdir(exist_ok=True)
        if not path.exists():
            KokoroTTS().synth("Bring your story to life with ReelHive.", path, voice.gender, voice.accent, voice.speed)
        return FileResponse(path, media_type="audio/wav")

    @app.get("/api/music")
    def music():
        from reelhive.audio.music_library import load_manifest

        return load_manifest()

    @app.get("/api/music/{name}")
    def music_file(name: str):
        from reelhive.audio.music_library import MUSIC_DIR, load_manifest

        if name not in {track["file"] for track in load_manifest()}:
            raise FileNotFoundError()
        return FileResponse(MUSIC_DIR / name, media_type="audio/mpeg")

    @app.post("/api/briefs/validate", response_model=Brief)
    def validate(brief: Brief):
        return brief

    @app.post("/api/briefs/import", response_model=Brief)
    def import_brief(value: YamlBrief):
        try:
            return Brief.model_validate(yaml.safe_load(value.text))
        except (yaml.YAMLError, ValidationError) as error:
            raise ValueError(str(error)) from error

    @app.post("/api/briefs/export")
    def export_brief(brief: Brief):
        return Response(yaml.safe_dump(brief.model_dump(mode="json"), sort_keys=False), media_type="application/yaml")

    @app.post("/api/runs", response_model=RunView)
    def create_run(value: CreateRun):
        return ws.create(value.brief, value.start)

    @app.get("/api/runs", response_model=list[RunView])
    def list_runs():
        return ws.list_runs()

    @app.get("/api/runs/{run_id}", response_model=RunView)
    def run(run_id: str):
        return ws.details(run_id)

    @app.post("/api/runs/{run_id}/start", status_code=202)
    def start(run_id: str, brief: Brief):
        ws.start(run_id, brief)
        return {"status": "started"}

    @app.post("/api/runs/{run_id}/script/approve", status_code=202)
    def approve_script(run_id: str, script: Script):
        ws.approve_script(run_id, script)
        return {"status": "queued"}

    @app.post("/api/runs/{run_id}/script/regenerate", status_code=202)
    def regenerate_script(run_id: str, value: Note):
        ws.regenerate_script(run_id, value.note)
        return {"status": "started"}

    @app.put("/api/runs/{run_id}/spec", status_code=202)
    def edit_spec(run_id: str, spec: SceneSpec):
        ws.edit_spec(run_id, spec)
        return {"status": "queued"}

    @app.post("/api/runs/{run_id}/scenes/{index}/regenerate", status_code=202)
    def regenerate_scene(run_id: str, index: int, value: Note):
        ws.regenerate_scene(run_id, index, value.note)
        return {"status": "queued"}

    @app.post("/api/runs/{run_id}/approve", status_code=202)
    def approve_scenes(run_id: str):
        ws.approve_scenes(run_id)
        return {"status": "queued"}

    @app.post("/api/runs/{run_id}/cancel", status_code=202)
    def cancel(run_id: str):
        ws.cancel(run_id)
        return {"status": "cancelling"}

    @app.post("/api/runs/{run_id}/resume", status_code=202)
    def resume(run_id: str):
        ws.resume(run_id)
        return {"status": "queued"}

    @app.get("/api/runs/{run_id}/events")
    async def events(run_id: str, request: Request, after: int = 0, follow: bool = True):
        ws.path(run_id)
        cursor = max(after, int(request.headers.get("last-event-id", "0")))

        async def stream():
            nonlocal cursor
            while not await request.is_disconnected():
                for event in ws.events(run_id, cursor):
                    cursor = event.id
                    yield f"id: {cursor}\ndata: {json.dumps(asdict(event))}\n\n"
                if not follow:
                    break
                yield ": heartbeat\n\n"
                await asyncio.sleep(1)

        return StreamingResponse(stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})

    @app.get("/api/runs/{run_id}/files/{name:path}")
    def download(run_id: str, name: str):
        return FileResponse(ws.file(run_id, name))

    @app.get("/api/runs/{run_id}/bundle.zip")
    def bundle(run_id: str):
        return Response(
            ws.bundle(run_id),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{run_id}.zip"'},
        )

    @app.post("/api/runs/{run_id}/reveal")
    def reveal(run_id: str):
        ws.reveal(run_id)
        return {"ok": True}

    @app.delete("/api/runs/{run_id}", status_code=204)
    def delete(run_id: str):
        ws.delete(run_id)

    @app.post("/api/uploads")
    async def upload(
        run_id: Annotated[str, Form()],
        file: Annotated[UploadFile, File()],
        caption: Annotated[str, Form()] = "",
        logo: Annotated[bool, Form()] = False,
    ):
        data = await file.read(10 * 1024 * 1024 + 1)
        return await asyncio.to_thread(ws.upload, run_id, data, file.filename or "", caption, logo)

    @app.post("/api/capture/test", response_model=list[str])
    def capture(value: CaptureRequest):
        return ws.test_capture(value.run_id, value.screenshots, value.format)

    @app.post("/api/login/start")
    def login_start(value: LoginRequest):
        Screenshots(url=value.url)
        return {"id": ws.login_start(value.run_id, value.url)}

    @app.get("/api/login/status")
    def login_status(id: str):
        return ws.login_status(id)

    @app.post("/api/login/finish")
    def login_finish(id: str):
        return ws.login_status(id, finish=True)

    ui = REPO_ROOT / "ui" / "dist"
    if (ui / "assets").exists():
        app.mount("/assets", StaticFiles(directory=ui / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path.startswith("api/"):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        if not (ui / "index.html").exists():
            return Response("Build the UI first: npm run build -w ui", status_code=503)
        return FileResponse(ui / "index.html")

    return app


def serve(config: Config, port: int = 0, open_browser: bool = True) -> None:
    import uvicorn

    host = "127.0.0.1"
    validate_host(host)
    app = create_app(config)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, port))
    sock.listen(128)
    url = f"http://{host}:{sock.getsockname()[1]}/?token={app.state.token}"
    print(f"ReelHive UI: {url}", flush=True)
    if open_browser:
        webbrowser.open(url)
    uvicorn.Server(uvicorn.Config(app, host=host, port=port, access_log=False)).run(sockets=[sock])
