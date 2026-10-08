"""Shared state for one run, passed to every node through Strands' invocation_state."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from reelhive.config import Config
from reelhive.core.events import EventBus
from reelhive.schemas.brief import Brief
from reelhive.schemas.scene_spec import SceneSpec
from reelhive.schemas.script import Script

if TYPE_CHECKING:
    from strands.models.model import Model

    from reelhive.audio.tts.base import TTS


@dataclass
class RunContext:
    run_dir: Path
    brief: Brief
    events: EventBus
    models: dict[str, Model]  # tier ("strong" | "fast") -> Strands model
    tts: TTS
    renderer: Callable[[Path, Path, Callable[[float], None]], None]  # (spec.json, out.mp4, on_progress)

    completed: set[str] = field(default_factory=set)
    voiced: dict[int, dict] = field(default_factory=dict)
    stage: str = "draft"
    note: str = ""
    lock: threading.RLock = field(default_factory=threading.RLock)
    config: Config = field(default_factory=Config)
    spec_only: bool = False  # evals: stop at the render contract, no video
    image_generator: Any = None  # visuals/generators/base.py ImageGenerator; None means configured OpenAI
    visual_catalog: list[dict[str, Any]] = field(default_factory=list)
    script: Script | None = None
    spec: SceneSpec | None = None
    narrated: dict[int, tuple[str, float]] = field(default_factory=dict)  # scene index -> (text, seconds)
    music: dict[str, Any] | None = None
    failures: list[str] = field(default_factory=list)  # hard-check or critic reasons for `fix`
    critic_passed: bool = False
    recheck_passed: bool = False
    video: Path | None = None

    def path(self, *parts: str) -> Path:
        p = self.run_dir.joinpath(*parts)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def checkpoint(self) -> None:
        with self.lock:
            data = {
                "completed": sorted(self.completed),
                "stage": self.stage,
                "script": self.script.model_dump() if self.script else None,
                "spec": self.spec.model_dump() if self.spec else None,
                "narrated": self.narrated,
                "voiced": self.voiced,
                "music": self.music,
                "visual_catalog": self.visual_catalog,
                "failures": self.failures,
                "critic_passed": self.critic_passed,
                "recheck_passed": self.recheck_passed,
            }
            temporary = self.path("checkpoint.tmp")
            temporary.write_text(json.dumps(data))
            temporary.replace(self.path("checkpoint.json"))
            if self.spec:
                self.path("spec.json").write_text(self.spec.model_dump_json(indent=2))

    def restore(self) -> None:
        from reelhive.schemas.scene_spec import SceneSpec
        from reelhive.schemas.script import Script

        data = json.loads(self.path("checkpoint.json").read_text())
        self.stage = data.get("stage", "draft")
        self.completed = set(data.get("completed", []))
        self.script = Script.model_validate(data["script"]) if data.get("script") else None
        self.spec = SceneSpec.model_validate(data["spec"]) if data.get("spec") else None
        self.narrated = {int(k): tuple(v) for k, v in data.get("narrated", {}).items()}
        self.voiced = {int(k): v for k, v in data.get("voiced", {}).items()}
        for key in ("music", "visual_catalog", "failures", "critic_passed", "recheck_passed"):
            if key in data:
                setattr(self, key, data[key])


class RunCancelled(RuntimeError):
    pass
