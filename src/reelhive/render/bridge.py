"""Python -> Node: run renderer/render.ts on a spec and stream its progress."""

from __future__ import annotations

import os
import subprocess
from collections import deque
from collections.abc import Callable
from pathlib import Path

from reelhive.config import REPO_ROOT

RENDERER_DIR = REPO_ROOT / "renderer"


class RenderError(RuntimeError):
    pass


def render(spec: Path, out: Path, on_progress: Callable[[float], None]) -> None:
    tsx = REPO_ROOT / "node_modules" / ".bin" / "tsx"
    if not tsx.exists():
        raise RenderError("renderer dependencies are missing; run `make setup` (npm ci)")
    proc = subprocess.Popen(
        [str(tsx), "render.ts", str(spec.resolve()), str(out.resolve())],
        cwd=RENDERER_DIR,
        env={**os.environ, "DISABLE_TELEMETRY": "true"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    tail: deque[str] = deque(maxlen=40)
    assert proc.stdout
    for line in proc.stdout:
        if line.startswith("progress "):
            on_progress(float(line.split()[1]))
        else:
            tail.append(line.rstrip())
    if proc.wait() != 0 or not out.exists():
        raise RenderError("renderer failed:\n" + "\n".join(tail))
