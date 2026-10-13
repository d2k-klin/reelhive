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
from reelhive.schemas.publish import PublishJob
from reelhive.schemas.scene_spec import SceneSpec, Word
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
    site_pages: list[dict[str, str]] = field(default_factory=list)  # research: pages read from the website
    research: dict[str, Any] | None = None  # research: product notes (also saved as research.json)
    script: Script | None = None
    spec: SceneSpec | None = None
    narrated: dict[int, tuple[str, float]] = field(default_factory=dict)  # scene index -> (text, seconds)
    words: dict[int, list[Word]] = field(default_factory=dict)  # scene index -> spoken words, timed from its audio
    music: dict[str, Any] | None = None
    failures: list[str] = field(default_factory=list)  # hard-check or critic reasons for `fix`
    critic_passed: bool = False
    recheck_passed: bool = False
    review_passed: bool | None = None  # None until the rendered cut has been reviewed
    review_rounds: int = 0  # failed reviews so far; the production graph bounds the repair loop
    plan_rounds: int = 0  # rechecks that still failed after a fix; the production graph bounds those repairs too
    video: Path | None = None
    publish: PublishJob | None = None  # publishing (publish/job.json): platforms, copy, and what each post became
    http: Any = None  # an httpx.Client for the platform adapters; None makes one per node (tests pass a mock)

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
                "words": {i: [w.model_dump() for w in ws] for i, ws in self.words.items()},
                "voiced": self.voiced,
                "music": self.music,
                "visual_catalog": self.visual_catalog,
                "research": self.research,
                "failures": self.failures,
                "critic_passed": self.critic_passed,
                "recheck_passed": self.recheck_passed,
                "review_passed": self.review_passed,
                "review_rounds": self.review_rounds,
                "plan_rounds": self.plan_rounds,
                "video": self.video.name if self.video and self.video.is_file() else None,
            }
            temporary = self.path("checkpoint.tmp")
            temporary.write_text(json.dumps(data))
            temporary.replace(self.path("checkpoint.json"))
            if self.spec:
                spec_temporary = self.path("spec.tmp")
                spec_temporary.write_text(self.spec.model_dump_json(indent=2))
                spec_temporary.replace(self.path("spec.json"))

    def save_publish(self) -> None:
        """Write the publishing job atomically; posting nodes call it after every post, so a crash never forgets one."""
        with self.lock:
            if self.publish is None:
                return
            temporary = self.path("publish", "job.tmp")
            temporary.write_text(self.publish.model_dump_json(indent=2))
            temporary.replace(self.path("publish", "job.json"))

    def restore(self) -> None:
        from reelhive.schemas.scene_spec import SceneSpec
        from reelhive.schemas.script import Script

        data = json.loads(self.path("checkpoint.json").read_text())
        self.stage = data.get("stage", "draft")
        self.completed = set(data.get("completed", []))
        self.script = Script.model_validate(data["script"]) if data.get("script") else None
        self.spec = SceneSpec.model_validate(data["spec"]) if data.get("spec") else None
        self.narrated = {int(k): tuple(v) for k, v in data.get("narrated", {}).items()}
        self.words = {int(k): [Word(**w) for w in v] for k, v in data.get("words", {}).items()}
        self.voiced = {int(k): v for k, v in data.get("voiced", {}).items()}
        for key in (
            "music",
            "visual_catalog",
            "research",
            "failures",
            "critic_passed",
            "recheck_passed",
            "review_passed",
            "review_rounds",
            "plan_rounds",
        ):
            if key in data:
                setattr(self, key, data[key])
        # A node counts as done only if what it made is still on disk.
        silent = self.path("render", "silent.mp4")
        if "render" in self.completed and not (silent.is_file() and silent.with_name("layout.json").is_file()):
            self.completed -= {"render", "review", "sound", "master"}
        video = self.path(data["video"]) if data.get("video") else self.path("video.mp4")
        if "master" in self.completed and video.is_file() and video.stat().st_size:
            self.video = video
        else:
            self.completed.discard("master")


class RunCancelled(RuntimeError):
    pass
