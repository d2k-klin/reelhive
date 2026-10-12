"""The user's own video clips: probed, then normalized so the renderer can play them frame-accurately.

A clip is shown muted inside a scene, from its first frame; when the scene outlasts it, the last frame holds.
Normalizing (H.264, constant 30 fps, no audio, no larger than the video, fast start) means every source format
the user drops in (`.mov` from a phone, `.webm` from a screen recorder) decodes the same way in the renderer,
and the rotation a phone records is applied once, here.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from reelhive.audio.mixer import ffmpeg_exe, probe
from reelhive.schemas.scene_spec import FORMATS

SUFFIXES = (".mp4", ".mov", ".m4v", ".webm")
MAX_SECONDS = 60.0  # the longest scene; anything past this would never be seen
MAX_BYTES = 200 * 1024 * 1024
MIN_SHORT_SIDE = 720  # a clip sits in a frame inside the shot, so either orientation works if it is this sharp
FPS = 30


class ClipError(ValueError):
    pass


def inspect(path: Path) -> dict[str, Any]:
    """Duration and display size of a playable clip; ClipError for anything else."""
    if path.suffix.lower() not in SUFFIXES:
        raise ClipError(f"{path.name}: clips must be {', '.join(SUFFIXES)}")
    if path.stat().st_size > MAX_BYTES:
        raise ClipError(f"{path.name}: clip exceeds {MAX_BYTES // (1024 * 1024)} MB")
    info = probe(path)
    duration, width, height = float(info["duration"]), int(info["width"]), int(info["height"])
    if not info["has_video"] or duration <= 0 or not width or not height:
        raise ClipError(f"{path.name}: not a playable video")
    return {"duration": round(min(duration, MAX_SECONDS), 3), "width": width, "height": height}


def sharp_enough(info: dict[str, Any]) -> bool:
    return min(info["width"], info["height"]) >= MIN_SHORT_SIDE


def _fingerprint(source: Path, format: str) -> str:
    stat = source.stat()
    return hashlib.sha256(
        json.dumps([str(source.resolve()), stat.st_size, stat.st_mtime_ns, format]).encode()
    ).hexdigest()


def normalize(source: Path, dest: Path, format: str) -> dict[str, Any]:
    """Re-encode `source` to `dest` for the renderer; returns the result's duration and size.

    Skipped when `dest` was already made from this exact source (a recheck re-resolves every scene)."""
    marker = dest.with_suffix(".json")
    fingerprint = _fingerprint(source, format)
    if dest.is_file() and marker.is_file():
        saved = json.loads(marker.read_text())
        if saved.get("fingerprint") == fingerprint:
            return saved["info"]
    width, height = FORMATS[format]
    # Fit inside the video's own size without enlarging, on even dimensions (H.264 4:2:0 needs them).
    fit = (
        f"scale='min({width},iw)':'min({height},ih)':force_original_aspect_ratio=decrease,"
        f"scale=trunc(iw/2)*2:trunc(ih/2)*2,fps={FPS},format=yuv420p"
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            ffmpeg_exe(),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-t",
            f"{MAX_SECONDS:g}",
            "-an",
            "-sn",
            "-vf",
            fit,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-movflags",
            "+faststart",
            str(dest),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise ClipError(f"{source.name}: could not convert the clip: {proc.stderr.strip()[-500:]}")
    info = inspect(dest)
    marker.write_text(json.dumps({"fingerprint": fingerprint, "info": info}))
    return info


def poster(source: Path, dest: Path, at: float) -> Path:
    """One frame of the clip as a JPEG: what the planner's describer and the studio's thumbnails see."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            ffmpeg_exe(),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{max(0.0, at):.3f}",
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-q:v",
            "3",
            str(dest),
        ],
        check=True,
        capture_output=True,
    )
    return dest
