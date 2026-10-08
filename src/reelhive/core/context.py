"""Shared state for one run, passed to every node through Strands' invocation_state."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

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
