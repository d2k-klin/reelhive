"""Python -> Node: run renderer/render.ts on a spec and stream its progress."""

from __future__ import annotations

import os
import subprocess
from collections import deque
from collections.abc import Callable
from pathlib import Path

from reelhive.config import REPO_ROOT
from reelhive.schemas.layout import LAYOUT_MARKER, LayoutReport

RENDERER_DIR = REPO_ROOT / "renderer"


class RenderError(RuntimeError):
    pass


def bundled_media_binaries(root: Path = REPO_ROOT) -> list[Path]:
    """The ffmpeg/ffprobe binaries Revideo ships through npm (@ffmpeg-installer, @ffprobe-installer)."""
    modules = root / "node_modules"
    return [
        *modules.glob("@ffmpeg-installer/*/ffmpeg"),
        *modules.glob("@ffprobe-installer/*/ffprobe"),
    ]


def ensure_executable(root: Path = REPO_ROOT) -> list[Path]:
    """Restore the execute bit an `npm ci --ignore-scripts` leaves off (their postinstall is `chmod u+x`).

    Without it the render finishes every frame and then dies on `spawn .../ffprobe EACCES`.
    Returns the binaries that were fixed.
    """
    if os.name == "nt":
        return []
    fixed = []
    for binary in bundled_media_binaries(root):
        if binary.is_file() and not os.access(binary, os.X_OK):
            binary.chmod(binary.stat().st_mode | 0o100)
            fixed.append(binary)
    return fixed


def layout_path(out: Path) -> Path:
    """Where a render's layout report lands: `layout.json` beside the silent video."""
    return out.with_name("layout.json")


def render(spec: Path, out: Path, on_progress: Callable[[float], None]) -> None:
    """Render `spec` to a silent `out`, and write what was measured on screen to `layout_path(out)`."""
    tsx = REPO_ROOT / "node_modules" / ".bin" / "tsx"
    if not tsx.exists():
        raise RenderError("renderer dependencies are missing; run `make setup` (npm ci)")
    ensure_executable()
    proc = subprocess.Popen(
        [str(tsx), "render.ts", str(spec.resolve()), str(out.resolve())],
        cwd=RENDERER_DIR,
        env={**os.environ, "DISABLE_TELEMETRY": "true"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    tail: deque[str] = deque(maxlen=40)
    measured: list[str] = []
    assert proc.stdout
    for line in proc.stdout:
        if line.startswith("progress "):
            on_progress(float(line.split()[1]))
        elif LAYOUT_MARKER in line:
            measured.append(line)
        else:
            tail.append(line.rstrip())
    if proc.wait() != 0 or not out.exists():
        output = "\n".join(tail)
        hint = ""
        if "EACCES" in output:
            hint = "\nHint: a bundled binary is not executable; run `npm rebuild` (or `make setup`) and resume the run."
        raise RenderError("renderer failed:\n" + output + hint)
    layout_path(out).write_text(LayoutReport.from_lines(measured).model_dump_json(indent=2))
