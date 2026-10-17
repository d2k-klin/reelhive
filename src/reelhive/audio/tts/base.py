from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import numpy as np

from reelhive.schemas.scene_spec import Word


@dataclass
class Speech:
    """What a TTS engine produced: the audio's length and its words, timed from the start of the audio."""

    seconds: float
    words: list[Word] = field(default_factory=list)


class TTS(Protocol):
    """Text to a WAV file. Piper (German) plugs in here later."""

    def synth(
        self, text: str, out: Path, gender: str, accent: str, speed: float, name: str | None = None
    ) -> Speech: ...


SILENCE = 0.01  # amplitude below which a 10 ms window counts as silence (about -40 dBFS)
GUARD_BEFORE = 0.04  # seconds kept before the first sound, so no onset is clipped
GUARD_AFTER = 0.08  # and after the last, so a trailing consonant can decay


def trim_silence(audio: np.ndarray, rate: int) -> tuple[np.ndarray, float]:
    """The clip without the silence an engine pads it with, and the seconds cut from its start (to shift word
    times by). Kokoro adds about 0.3 s before and 0.5 s after every clip; timing adds its own pauses (LEAD, TAILS),
    so left in, every beat would carry both, and a script of many short beats would run long."""
    window = max(1, int(rate * 0.01))
    frames = len(audio) // window
    if frames == 0:
        return audio, 0.0
    peaks = np.abs(audio[: frames * window]).reshape(frames, window).max(axis=1)
    loud = np.flatnonzero(peaks > SILENCE)
    if not len(loud):
        return audio, 0.0
    start = max(0, loud[0] * window - int(GUARD_BEFORE * rate))
    end = min(len(audio), (loud[-1] + 1) * window + int(GUARD_AFTER * rate))
    return audio[start:end], start / rate


def shift_words(words: list[Word], by: float, seconds: float) -> list[Word]:
    """Word times moved `by` seconds earlier, kept inside a clip `seconds` long."""
    return [
        Word(
            text=w.text,
            start=round(min(max(0.0, w.start - by), seconds), 3),
            end=round(min(max(0.0, w.end - by), seconds), 3),
        )
        for w in words
    ]


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
