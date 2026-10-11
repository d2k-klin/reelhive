from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from reelhive.schemas.scene_spec import Word


@dataclass
class Speech:
    """What a TTS engine produced: the audio's length and its words, timed from the start of the audio."""

    seconds: float
    words: list[Word] = field(default_factory=list)


class TTS(Protocol):
    """Text to a WAV file. Piper (German) plugs in here later."""

    def synth(self, text: str, out: Path, gender: str, accent: str, speed: float) -> Speech: ...


def estimate_words(text: str, start: float, seconds: float) -> list[Word]:
    """Words spread over `seconds` by their length, for engines (or chunks) that report no timestamps."""
    words = re.findall(r"\S+", text)
    weights = [len(re.sub(r"\W", "", w)) + 1 for w in words]
    total, clock, timed = sum(weights) or 1, start, []
    for word, weight in zip(words, weights, strict=True):
        length = seconds * weight / total
        timed.append(Word(text=word, start=round(clock, 3), end=round(clock + length, 3)))
        clock += length
    return timed
