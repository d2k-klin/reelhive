"""Generate the placeholder music library (assets/music) with a tiny synth.

These tracks are our own work, dedicated to the public domain (CC0-1.0). They stand in until
the curated CC0 set is chosen (plan §14, open decision 3). Run: python scripts/make_music.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from reelhive.audio.mixer import ffmpeg_exe  # noqa: E402

SR = 44100
OUT = Path(__file__).resolve().parents[1] / "assets" / "music"

# mood: (bpm, chord progression as MIDI notes, drums)
TRACKS = {
    "upbeat": (120, [[60, 64, 67], [67, 71, 74], [69, 72, 76], [65, 69, 72]], True),
    "calm": (80, [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]], False),
    "inspiring": (100, [[62, 66, 69], [59, 62, 66], [55, 59, 62], [57, 61, 64]], False),
    "tech": (110, [[57, 60, 64], [57, 60, 65], [55, 59, 62], [53, 57, 60]], True),
    "dramatic": (90, [[50, 53, 57], [46, 50, 53], [53, 57, 60], [52, 55, 59]], False),
}


def hz(note: int) -> float:
    return 440.0 * 2 ** ((note - 69) / 12)


def tone(freq: float, seconds: float, harmonics=(1.0, 0.35, 0.15)) -> np.ndarray:
    t = np.arange(int(seconds * SR)) / SR
    wave = sum(a * np.sin(2 * np.pi * freq * (i + 1) * t) for i, a in enumerate(harmonics))
    attack, release = min(int(0.4 * SR), len(t) // 4), min(int(0.8 * SR), len(t) // 2)
    env = np.ones_like(t)
    env[:attack] = np.linspace(0, 1, attack)
    env[-release:] = np.linspace(1, 0, release)
    return wave * env


def track(bpm: int, chords: list[list[int]], drums: bool, bars: int = 32) -> np.ndarray:
    beat = 60 / bpm
    bar = 4 * beat
    out = np.zeros(int(bars * bar * SR) + SR)
    for b in range(bars):
        chord = chords[b % len(chords)]
        at = int(b * bar * SR)
        pad = sum(tone(hz(n), bar + 0.6) for n in chord) / len(chord)
        bass = tone(hz(chord[0] - 12), bar + 0.6, harmonics=(1.0, 0.2))
        seg = 0.5 * pad + 0.35 * bass
        out[at : at + len(seg)] += seg[: len(out) - at]
        for k in range(8):  # gentle arpeggio in eighths
            note = tone(hz(chord[k % 3] + 12), beat / 2, harmonics=(1.0, 0.1))
            note *= np.exp(-np.linspace(0, 6, len(note)))
            s = at + int(k * beat / 2 * SR)
            out[s : s + len(note)] += 0.18 * note[: len(out) - s]
        if drums:
            for k in range(4):
                n = int(0.25 * SR)
                t = np.arange(n) / SR
                kick = np.sin(2 * np.pi * (50 + 80 * np.exp(-t * 30)) * t) * np.exp(-t * 12)
                s = at + int(k * beat * SR)
                out[s : s + n] += 0.5 * kick[: len(out) - s]
    out = out[: int(bars * bar * SR)]
    return (out / np.max(np.abs(out)) * 0.8).astype(np.float32)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for mood, (bpm, chords, drums) in TRACKS.items():
        audio = track(bpm, chords, drums)
        name = f"{mood}-{bpm}.mp3"
        subprocess.run(
            [
                ffmpeg_exe(),
                "-y",
                "-loglevel",
                "error",
                "-f",
                "f32le",
                "-ar",
                str(SR),
                "-ac",
                "1",
                "-i",
                "-",
                "-c:a",
                "libmp3lame",
                "-b:a",
                "128k",
                str(OUT / name),
            ],
            input=audio.tobytes(),
            check=True,
        )
        manifest.append(
            {
                "file": name,
                "title": f"ReelHive placeholder ({mood})",
                "mood": mood,
                "bpm": bpm,
                "duration": round(len(audio) / SR, 2),
                "source": "scripts/make_music.py",
                "license": "CC0-1.0",
            }
        )
    (OUT / "manifest.json").write_text(json.dumps({"tracks": manifest}, indent=2) + "\n")


if __name__ == "__main__":
    main()
