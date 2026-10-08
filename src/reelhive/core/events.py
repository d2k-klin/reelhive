"""One event stream for the CLI, the UI (M3) and run.log.jsonl (plan §3.8)."""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

EVENT_TYPES = {
    "node.started",
    "node.finished",
    "node.skipped",
    "node.task",
    "agent.text",
    "gate.result",
    "critic.verdict",
    "fix.diff",
    "run.finished",
    "run.paused",
    "script.approved",
    "suggestion.offered",
    "suggestion.applied",  # emitted by the regenerate path (M3) when a suggestion's note is used
    "run.queued",
    "run.cancelled",
    "spec.edited",
}


@dataclass
class Event:
    type: str
    data: dict[str, Any]
    ts: float = field(default_factory=time.time)
    id: int = 0


class EventBus:
    """Fans events out to subscribers and appends each one to the run log."""

    def __init__(self, log_path: Path | None = None) -> None:
        self.log_path = log_path
        self._subscribers: list[Callable[[Event], None]] = []
        self._next_id = len(log_path.read_text().splitlines()) + 1 if log_path and log_path.exists() else 1
        self._lock = threading.Lock()  # nodes run in worker threads

    def subscribe(self, fn: Callable[[Event], None]) -> None:
        self._subscribers.append(fn)

    def emit(self, type: str, **data: Any) -> Event:
        if type not in EVENT_TYPES:
            raise ValueError(f"unknown event type {type!r}")
        event = Event(type, data)
        with self._lock:
            event.id = self._next_id
            self._next_id += 1
            if self.log_path:
                with self.log_path.open("a") as f:
                    f.write(json.dumps(asdict(event), default=str) + "\n")
            for fn in self._subscribers:
                fn(event)
        return event


def replay(log_path: Path) -> list[Event]:
    """Read a run log back into events, e.g. to rebuild a past run's state."""
    return [Event(**json.loads(line)) for line in log_path.read_text().splitlines() if line.strip()]
