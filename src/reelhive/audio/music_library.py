"""The curated CC0 music library in assets/music (plan §2: no generated music at run time)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reelhive.config import REPO_ROOT

MUSIC_DIR = REPO_ROOT / "assets" / "music"
MOODS = ("upbeat", "calm", "inspiring", "tech", "dramatic")


def load_manifest(music_dir: Path = MUSIC_DIR) -> list[dict[str, Any]]:
    return json.loads((music_dir / "manifest.json").read_text())["tracks"]


def pick_track(mood: str, bpm: int, music_dir: Path = MUSIC_DIR) -> dict[str, Any]:
    """Closest tempo within the mood; any mood if the mood has no tracks."""
    tracks = load_manifest(music_dir)
    pool = [t for t in tracks if t["mood"] == mood] or tracks
    best = min(pool, key=lambda t: abs(t["bpm"] - bpm))
    return {**best, "file": str(music_dir / best["file"])}
