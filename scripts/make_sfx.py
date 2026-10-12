"""Synthesize the CC0 sound-effect library in assets/sfx and its manifest.json.

uv run python scripts/make_sfx.py

Six quiet, short effects for motion graphics. Each is made from filtered noise and decaying tones with a fixed
seed, so the files are reproducible. `peak` is the second the effect is loudest: the `sound` node lines that up
with the on-screen moment it scores. `suits` lists the moment kinds (renderer/src/measure.ts `Moment`) the
effect is allowed on.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import soundfile as sf

RATE = 48000
OUT = Path(__file__).resolve().parents[1] / "assets" / "sfx"
rng = np.random.default_rng(7)


def seconds(length: float) -> np.ndarray:
    return np.arange(int(length * RATE)) / RATE


def bandpass(signal: np.ndarray, centre: np.ndarray, width: float) -> np.ndarray:
    """A state-variable band-pass whose centre frequency can move sample by sample (for sweeps)."""
    low = band = 0.0
    out = np.empty_like(signal)
    damping = 1.0 / width
    for i, x in enumerate(signal):
        f = 2 * np.sin(np.pi * min(centre[i], RATE / 6) / RATE)
        low += f * band
        high = x - low - damping * band
        band += f * high
        out[i] = band
    return out


def fade(sound: np.ndarray, attack: float, release: float) -> np.ndarray:
    n = len(sound)
    env = np.ones(n)
    a, r = int(attack * RATE), int(release * RATE)
    if a:
        env[:a] = np.linspace(0, 1, a) ** 2
    if r:
        env[n - r :] *= np.linspace(1, 0, r) ** 2
    return sound * env


def normalize(sound: np.ndarray, peak_db: float = -3.0) -> np.ndarray:
    return sound / np.max(np.abs(sound)) * 10 ** (peak_db / 20)


def whoosh(length: float, low: float, high: float, peak: float) -> np.ndarray:
    """Air moving past: band-passed noise sweeping up to `high` at `peak`, then back down, swelling with it."""
    t = seconds(length)
    shape = np.where(t < peak, (t / peak) ** 2, np.exp(-(t - peak) / ((length - peak) / 3.5)))
    centre = low + (high - low) * shape
    return fade(bandpass(rng.standard_normal(len(t)), centre, 1.6) * shape, 0.01, 0.05)


def click(length: float = 0.12) -> np.ndarray:
    """A soft UI click: a 2 ms transient on a short, high, quickly damped body."""
    t = seconds(length)
    body = np.sin(2 * np.pi * 2400 * t) * np.exp(-t / 0.012) + 0.5 * np.sin(2 * np.pi * 5200 * t) * np.exp(-t / 0.006)
    transient = rng.standard_normal(len(t)) * np.exp(-t / 0.002)
    return fade(body + 0.6 * transient, 0.0005, 0.02)


def pop(length: float = 0.25) -> np.ndarray:
    """A rounded pop: a sine dropping from 900 to 300 Hz in a few milliseconds."""
    t = seconds(length)
    pitch = 300 + 600 * np.exp(-t / 0.015)
    phase = 2 * np.pi * np.cumsum(pitch) / RATE
    return fade(np.sin(phase) * np.exp(-t / 0.05), 0.001, 0.05)


def chime(length: float = 1.8) -> np.ndarray:
    """Two bell partials a fifth apart (E6 and B6) with slightly inharmonic overtones, ringing out."""
    t = seconds(length)
    tone = np.zeros_like(t)
    for freq, amp, decay in (
        (1318.5, 1.0, 0.55),
        (1975.5, 0.6, 0.42),
        (2637.0 * 1.003, 0.25, 0.22),
        (3951.1, 0.12, 0.15),
    ):
        tone += amp * np.sin(2 * np.pi * freq * t) * np.exp(-t / decay)
    return fade(tone, 0.002, 0.3)


def soft_impact(length: float = 0.9) -> np.ndarray:
    """A low, felt-not-heard thump with a little air on top, for a settle into the closing frame."""
    t = seconds(length)
    pitch = 55 + 45 * np.exp(-t / 0.04)
    body = np.sin(2 * np.pi * np.cumsum(pitch) / RATE) * np.exp(-t / 0.22)
    air = bandpass(rng.standard_normal(len(t)), np.full(len(t), 900.0), 0.9) * np.exp(-t / 0.08)
    return fade(body + 0.35 * air, 0.003, 0.2)


def peak_of(sound: np.ndarray) -> float:
    window = int(0.01 * RATE)
    energy = np.convolve(sound**2, np.ones(window) / window, mode="same")
    return round(float(np.argmax(energy)) / RATE, 3)


EFFECTS = [
    (
        "whoosh-soft",
        lambda: whoosh(0.7, 250, 3200, 0.38),
        "Soft whoosh of air, for a shot pushing in from the side",
        ["cut"],
    ),
    (
        "swish-short",
        lambda: whoosh(0.4, 600, 5200, 0.2),
        "Short, bright swish, for the device gliding into its next place",
        ["cut"],
    ),
    ("click-ui", click, "Quiet interface click, for the camera landing on a button or control", ["focus"]),
    ("pop-soft", pop, "Rounded pop, for a number or point landing on screen", ["arrive"]),
    ("chime-bright", chime, "Two-note bell, for the closing call to action or the logo arriving", ["arrive"]),
    ("impact-low", soft_impact, "Low, soft thump, for settling into the intro or the closing frame", ["cut", "arrive"]),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    effects = []
    for name, make, description, suits in EFFECTS:
        sound = normalize(make())
        sf.write(OUT / f"{name}.wav", sound.astype(np.float32), RATE, subtype="PCM_16")
        effects.append(
            {
                "file": f"{name}.wav",
                "name": name,
                "description": description,
                "suits": suits,
                "duration": round(len(sound) / RATE, 3),
                "peak": peak_of(sound),
                "source": "scripts/make_sfx.py",
                "license": "CC0-1.0",
            }
        )
    (OUT / "manifest.json").write_text(json.dumps({"effects": effects}, indent=2) + "\n")
    print(f"wrote {len(effects)} effects to {OUT}")


if __name__ == "__main__":
    main()
