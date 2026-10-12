"""Narration + music mix with sidechain ducking, and the final mux (plan §3.2 `render`)."""

from __future__ import annotations

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
MUSIC_VOLUME = 0.3  # under the voice, before ducking
FADE_OUT = 2.0


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


def mix_args(
    narration: Path, music: Path | None, duration: float, out: Path, volume: float = MUSIC_VOLUME
) -> list[str]:
    if music is None:
        return ["-i", str(narration), "-ac", "2", "-ar", "48000", "-t", f"{duration:.3f}", str(out)]
    fade_at = max(0.0, duration - FADE_OUT)
    graph = (
        f"[0:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={volume},"
        f"afade=t=in:d=1,afade=t=out:st={fade_at:.3f}:d={FADE_OUT}[music];"
        "[1:a]aformat=sample_rates=48000:channel_layouts=stereo,asplit=2[voice][key];"
        "[music][key]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[ducked];"
        "[ducked][voice]amix=inputs=2:duration=first:normalize=0[out]"
    )
    return [
        "-stream_loop",
        "-1",
        "-i",
        str(music),
        "-i",
        str(narration),
        "-filter_complex",
        graph,
        "-map",
        "[out]",
        "-t",
        f"{duration:.3f}",
        str(out),
    ]


def mix(run_dir: Path, spec: SceneSpec, narration: bool = True) -> Path:
    audio = run_dir / "audio"
    audio.mkdir(exist_ok=True)
    voice = narration_track(run_dir, spec, audio / "narration.wav", narration)
    out = audio / "mix.wav"
    _run(mix_args(voice, Path(spec.music) if spec.music else None, spec.duration, out, spec.music_volume))
    return out


def mux_args(video: Path, audio: Path, out: Path, subtitles: Path | None = None) -> list[str]:
    """The reviewed cut, the mix and, when given, a soft (selectable) English subtitle track."""
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
        "-shortest",
        "-movflags",
        "+faststart",
        "-metadata",
        f"comment={CREDIT_TEXT}",
        str(out),
    ]


def mux(video: Path, audio: Path, out: Path, subtitles: Path | None = None) -> Path:
    _run(mux_args(video, audio, out, subtitles))
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
