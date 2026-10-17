"""Narration + music mix with sidechain ducking, loudness to the platforms' target, and the final mux."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

from reelhive.nodes.timing_node import LEAD
from reelhive.schemas.scene_spec import CREDIT_TEXT, SceneSpec

SAMPLE_RATE = 24000
EFFECTS_RATE = 48000  # assets/sfx is 48 kHz: clicks and air need the top octave the voice doesn't
MUSIC_VOLUME = 0.3  # under the voice, before ducking
FADE_OUT = 2.0
# What YouTube, Instagram, TikTok and Spotify turn playback to: master here, so the video isn't turned down (and
# squashed) or left quieter than the one before it in the feed.
LOUDNESS = "I=-14:TP=-1:LRA=11"
SILENT = -70.0  # LUFS: below this there is nothing to bring up (no voice, no music)


def ffmpeg_exe() -> str:
    """System ffmpeg if installed, else the static build that ships with imageio-ffmpeg."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    import imageio_ffmpeg

    return str(imageio_ffmpeg.get_ffmpeg_exe())


def _run(args: list[str]) -> None:
    proc = subprocess.run(
        [ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", *args], capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr.strip()[-2000:]}")


def narration_track(run_dir: Path, spec: SceneSpec, out: Path, voice_on: bool = True) -> Path:
    """Place each scene's voice at its scene start + LEAD on one silent timeline (left silent when voice is off)."""
    track = np.zeros(int(spec.duration * SAMPLE_RATE) + SAMPLE_RATE, dtype=np.float32)
    for scene in spec.scenes:
        if not scene.audio or not voice_on:
            continue
        voice, sr = sf.read(run_dir / scene.audio, dtype="float32")
        if sr != SAMPLE_RATE:
            raise ValueError(f"{scene.audio}: expected {SAMPLE_RATE} Hz, got {sr}")
        if voice.ndim > 1:
            voice = voice.mean(axis=1)
        at = int((scene.start + LEAD) * SAMPLE_RATE)
        end = min(len(track), at + len(voice))
        track[at:end] += voice[: end - at]
    sf.write(out, track[: int(spec.duration * SAMPLE_RATE)], SAMPLE_RATE)
    return out


def effects_track(spec: SceneSpec, out: Path, sfx_dir: Path | None = None) -> Path:
    """Place each sound effect at its `at` and level on one silent 48 kHz timeline (one file, like the voice)."""
    from reelhive.audio.sfx_library import SFX_DIR

    folder = sfx_dir or SFX_DIR
    track = np.zeros(int(spec.duration * EFFECTS_RATE) + EFFECTS_RATE, dtype=np.float32)
    for cue in spec.sound_effects:
        effect, rate = sf.read(folder / cue.effect, dtype="float32")
        if rate != EFFECTS_RATE:
            raise ValueError(f"{cue.effect}: expected {EFFECTS_RATE} Hz, got {rate}")
        if effect.ndim > 1:
            effect = effect.mean(axis=1)
        at = int(cue.at * EFFECTS_RATE)
        end = min(len(track), at + len(effect))
        track[at:end] += effect[: end - at] * 10 ** (cue.gain_db / 20)
    sf.write(out, track[: int(spec.duration * EFFECTS_RATE)], EFFECTS_RATE)
    return out


def mix_args(
    narration: Path,
    music: Path | None,
    duration: float,
    out: Path,
    volume: float = MUSIC_VOLUME,
    effects: Path | None = None,
) -> list[str]:
    """One ffmpeg call: the music (looped, faded, ducked under the voice), the voice, and the effects, summed."""
    if music is None and effects is None:
        return ["-i", str(narration), "-ac", "2", "-ar", "48000", "-t", f"{duration:.3f}", str(out)]
    stereo = "aformat=sample_rates=48000:channel_layouts=stereo"
    inputs: list[str] = []
    chains: list[str] = []
    mixed: list[str] = []
    if music is not None:
        inputs += ["-stream_loop", "-1", "-i", str(music)]
    inputs += ["-i", str(narration)]
    voice = 1 if music is not None else 0  # input index of the narration
    if music is not None:
        fade_at = max(0.0, duration - FADE_OUT)
        chains += [
            f"[0:a]{stereo},volume={volume},afade=t=in:d=1,afade=t=out:st={fade_at:.3f}:d={FADE_OUT}[music]",
            f"[{voice}:a]{stereo},asplit=2[voice][key]",
            "[music][key]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[ducked]",
        ]
        mixed += ["[ducked]", "[voice]"]
    else:
        chains.append(f"[{voice}:a]{stereo}[voice]")
        mixed.append("[voice]")
    if effects is not None:
        inputs += ["-i", str(effects)]
        chains.append(f"[{voice + 1}:a]{stereo}[effects]")
        mixed.append("[effects]")
    graph = ";".join([*chains, f"{''.join(mixed)}amix=inputs={len(mixed)}:duration=first:normalize=0[out]"])
    return [*inputs, "-filter_complex", graph, "-map", "[out]", "-t", f"{duration:.3f}", str(out)]


def measure_loudness(path: Path) -> dict[str, str]:
    """ffmpeg's loudnorm measurement of a file: integrated loudness, true peak, range, threshold and offset."""
    proc = subprocess.run(
        [
            ffmpeg_exe(),
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-af",
            f"loudnorm={LOUDNESS}:print_format=json",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    )
    found = re.findall(r"\{[^{}]*\}", proc.stderr)  # the report; ffmpeg may log more lines after it
    if proc.returncode != 0 or not found:
        raise RuntimeError(f"ffmpeg could not measure loudness: {proc.stderr.strip()[-2000:]}")
    return json.loads(found[-1])


def normalize(src: Path, out: Path) -> Path:
    """Two passes: measure, then one linear gain onto the target, so the mix keeps its dynamics (no pumping).
    loudnorm falls back to gentle dynamic gain only where a linear one would clip the true-peak ceiling."""
    m = measure_loudness(src)
    if float(m["input_i"]) < SILENT:
        shutil.copyfile(src, out)
        return out
    measured = (
        f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
        f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}"
    )
    # loudnorm works at 192 kHz inside; -ar brings it back to the mix's rate.
    _run(["-i", str(src), "-af", f"loudnorm={LOUDNESS}:{measured}:linear=true", "-ar", "48000", str(out)])
    return out


def mix(run_dir: Path, spec: SceneSpec, narration: bool = True) -> Path:
    audio = run_dir / "audio"
    audio.mkdir(exist_ok=True)
    voice = narration_track(run_dir, spec, audio / "narration.wav", narration)
    effects = effects_track(spec, audio / "effects.wav") if spec.sound_effects else None
    raw = audio / "mix.raw.wav"
    music = Path(spec.music) if spec.music else None
    _run(mix_args(voice, music, spec.duration, raw, spec.music_volume, effects))
    out = normalize(raw, audio / "mix.wav")
    raw.unlink()
    return out


def mux_args(
    video: Path, audio: Path, out: Path, subtitles: Path | None = None, duration: float | None = None
) -> list[str]:
    """The reviewed cut, the mix and, when given, a soft (selectable) English subtitle track.

    The length is the spec's `duration` when given. `-shortest` alone would count the subtitle stream too, which
    ends with the last spoken word, and cut the closing frame and the credit."""
    # The metadata tag is always written, even with the visible credit off (plan §3.7).
    inputs = ["-i", str(video), "-i", str(audio)]
    maps = ["-map", "0:v", "-map", "1:a"]
    if subtitles:
        inputs += ["-i", str(subtitles)]
        maps += ["-map", "2:s", "-c:s", "mov_text", "-metadata:s:s:0", "language=eng"]
    return [
        *inputs,
        *maps,
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        *(["-t", f"{duration:.3f}"] if duration else ["-shortest"]),
        "-movflags",
        "+faststart",
        "-metadata",
        f"comment={CREDIT_TEXT}",
        str(out),
    ]


def mux(video: Path, audio: Path, out: Path, subtitles: Path | None = None, duration: float | None = None) -> Path:
    _run(mux_args(video, audio, out, subtitles, duration))
    return out


def probe(path: Path) -> dict[str, Any]:
    """Duration, streams, display size (rotation applied) and comment tag, parsed from `ffmpeg -i` (no ffprobe)."""
    info = subprocess.run([ffmpeg_exe(), "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    d = re.search(r"Duration: (\d+):(\d+):([\d.]+)", info)
    size = re.search(r"Video: .*?, (\d{2,5})x(\d{2,5})", info)
    comment = re.search(r"comment\s*:\s*(.+)", info)
    rotation = re.search(r"rotation of (-?[\d.]+) degrees", info)
    width, height = (int(size[1]), int(size[2])) if size else (0, 0)
    if rotation and round(abs(float(rotation[1]))) % 180 == 90:  # a phone held upright: the size it is shown at
        width, height = height, width
    return {
        "duration": int(d[1]) * 3600 + int(d[2]) * 60 + float(d[3]) if d else 0.0,
        "has_audio": "Audio:" in info,
        "has_video": "Video:" in info,
        "has_subtitles": "Subtitle:" in info,
        "width": width,
        "height": height,
        "comment": comment[1].strip() if comment else None,
    }
