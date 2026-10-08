from __future__ import annotations

from pathlib import Path
from typing import Protocol


class TTS(Protocol):
    """Text to a WAV file; returns the audio length in seconds. Piper (German) plugs in here later."""

    def synth(self, text: str, out: Path, gender: str, accent: str, speed: float) -> float: ...
