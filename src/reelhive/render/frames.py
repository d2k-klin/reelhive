"""Settled stills from the silent render, one per shot, for the frame review."""

from __future__ import annotations

import subprocess
from pathlib import Path

from reelhive.audio.mixer import ffmpeg_exe
from reelhive.schemas.scene_spec import Intro, SceneSpec

SETTLED = 0.7  # how far into a shot its still is taken: after the entrance, before the next transition


def shot_times(spec: SceneSpec) -> list[tuple[str, int, float]]:
    """(kind, index, seconds) of each shot's settled moment, in playing order; the intro has index 0."""
    times, clock = [], 0.0
    for item in spec.timeline():
        if isinstance(item, Intro):
            times.append(("intro", 0, clock + item.duration * SETTLED))
            clock += item.duration
        else:
            times.append(("scene", item.index, item.start + item.duration * SETTLED))
            clock = item.start + item.duration
    return times


def keyframes(video: Path, spec: SceneSpec, folder: Path) -> list[tuple[str, int, Path]]:
    """Extract one JPEG per shot into `folder`; returns (kind, index, file) in playing order."""
    folder.mkdir(parents=True, exist_ok=True)
    frames = []
    for kind, index, seconds in shot_times(spec):
        out = folder / ("intro.jpg" if kind == "intro" else f"scene_{index:02d}.jpg")
        proc = subprocess.run(
            [
                ffmpeg_exe(),
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                f"{seconds:.3f}",
                "-i",
                str(video),
                "-frames:v",
                "1",
                "-q:v",
                "3",
                str(out),
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0 or not out.is_file():
            raise RuntimeError(f"could not extract the {kind} {index} frame: {proc.stderr.strip()[-500:]}")
        frames.append((kind, index, out))
    return frames
