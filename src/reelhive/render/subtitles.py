"""Subtitle files from the recorded voice: `video.srt` and `video.vtt` beside the video.

The cues are the same short phrases the renderer burns in (renderer/src/components/captions.tsx `phrases()`),
built from the same word timings, so a platform's closed captions and the on-screen captions never disagree.
The phrasing constants are contract-tested against the renderer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from reelhive.schemas.scene_spec import SceneSpec

MAX_WORDS = 4
MAX_CHARS = 28
LINGER = 0.4  # a phrase stays this long after its last word, unless the next one starts sooner
BREAK = re.compile(r"[.,!?;:]$")


@dataclass(frozen=True)
class Cue:
    start: float
    end: float
    text: str


def cues(spec: SceneSpec) -> list[Cue]:
    """Short phrases on the video clock: a break after punctuation, or at four words / 28 characters."""
    phrases: list[list[tuple[str, float, float]]] = []
    for scene in spec.scenes:
        current: list[tuple[str, float, float]] = []
        for word in scene.words:
            timed = (word.text, scene.start + word.start, scene.start + word.end)
            length = len(" ".join(w[0] for w in [*current, timed]))
            if len(current) >= MAX_WORDS or (current and length > MAX_CHARS):
                phrases.append(current)
                current = []
            current.append(timed)
            if BREAK.search(word.text):
                phrases.append(current)
                current = []
        if current:
            phrases.append(current)
    result = []
    for i, phrase in enumerate(phrases):
        following = phrases[i + 1][0][1] if i + 1 < len(phrases) else float("inf")
        end = min(phrase[-1][2] + LINGER, following, spec.duration or float("inf"))
        result.append(Cue(round(phrase[0][1], 3), round(end, 3), " ".join(w[0] for w in phrase)))
    return result


def _clock(seconds: float, separator: str) -> str:
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{millis:03d}"


def srt(items: list[Cue]) -> str:
    blocks = [f"{n}\n{_clock(c.start, ',')} --> {_clock(c.end, ',')}\n{c.text}\n" for n, c in enumerate(items, start=1)]
    return "\n".join(blocks)


def vtt(items: list[Cue]) -> str:
    blocks = [f"{_clock(c.start, '.')} --> {_clock(c.end, '.')}\n{c.text}\n" for c in items]
    return "WEBVTT\n\n" + "\n".join(blocks)


def write(spec: SceneSpec, video: Path, voiced: bool = True) -> list[Path]:
    """Write `<video>.srt` and `<video>.vtt`. Subtitles transcribe the voice, so a video without narration (or
    without spoken words) gets none, and any from an earlier master are removed."""
    items = cues(spec) if voiced else []
    if not items:
        for suffix in (".srt", ".vtt"):
            video.with_suffix(suffix).unlink(missing_ok=True)
        return []
    written = []
    for suffix, text in ((".srt", srt(items)), (".vtt", vtt(items))):
        path = video.with_suffix(suffix)
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written
