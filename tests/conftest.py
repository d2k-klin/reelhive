"""Fakes that implement the real interfaces, so CI needs no API keys, no Kokoro and no Node."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import soundfile as sf
import yaml
from strands.models.model import Model

from reelhive.audio.mixer import ffmpeg_exe
from reelhive.audio.tts.base import Speech, estimate_words
from reelhive.config import REPO_ROOT, Config
from reelhive.render.bridge import layout_path
from reelhive.schemas.brief import Brief
from reelhive.schemas.layout import Box, LayoutReport, ShotLayout
from reelhive.schemas.scene_spec import Intro, SceneSpec

WORDS_PER_SECOND = 2.6  # ~156 wpm, close to Kokoro at speed 1.0


class FakeModel(Model):
    """A Strands model that answers every structured-output request with canned JSON.

    `responses` maps the output model's name (e.g. "Script") to a dict, or to a list of dicts
    consumed in order. Asking for a name with no response fails the test loudly.
    """

    def __init__(self, responses: dict[str, Any]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def update_config(self, **model_config: Any) -> None:
        pass

    def get_config(self) -> Any:
        return {}

    def _next(self, name: str) -> dict[str, Any]:
        self.calls.append(name)
        value = self.responses[name]
        return value.pop(0) if isinstance(value, list) else value

    async def structured_output(self, output_model, prompt, system_prompt=None, **kwargs):  # type: ignore[override]
        yield {"output": output_model(**self._next(output_model.__name__))}

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):  # type: ignore[override]
        name = tool_specs[0]["name"]
        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockDelta": {"delta": {"text": f"thinking about {name}"}}}
        yield {"contentBlockStop": {}}
        yield {"contentBlockStart": {"start": {"toolUse": {"toolUseId": f"t{len(self.calls)}", "name": name}}}}
        yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(self._next(name))}}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "tool_use"}}
        yield {
            "metadata": {
                "usage": {"inputTokens": 100, "outputTokens": 50, "totalTokens": 150},
                "metrics": {"latencyMs": 1},
            }
        }


class StubTTS:
    """Writes silence as long as the words would take to say."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.voices: list[str | None] = []

    def synth(self, text: str, out: Path, gender: str, accent: str, speed: float, name: str | None = None) -> Speech:
        self.calls.append(text)
        self.voices.append(name)
        seconds = len(text.split()) / WORDS_PER_SECOND / speed
        sf.write(out, np.zeros(int(seconds * 24000), dtype=np.float32), 24000)
        return Speech(seconds, estimate_words(text, 0.0, seconds))


def stub_layout(spec: SceneSpec) -> LayoutReport:
    """What a clean render measures: one headline per shot, centred well inside the safe area."""
    w, h = spec.width, spec.height
    headline = Box(role="headline", x=w * 0.2, y=h * 0.4, width=w * 0.6, height=h * 0.1, font_size=h * 0.05)
    return LayoutReport(
        shots=[
            ShotLayout(kind="intro", index=0, width=w, height=h, boxes=[headline])
            if isinstance(item, Intro)
            else ShotLayout(kind="scene", index=item.index, width=w, height=h, boxes=[headline])
            for item in spec.timeline()
        ]
    )


def stub_renderer(spec: Path, out: Path, on_progress: Callable[[float], None]) -> None:
    """A black video as long as the spec, made by ffmpeg instead of Revideo, plus a clean layout report."""
    duration = json.loads(spec.read_text())["duration"]
    layout_path(out).write_text(stub_layout(SceneSpec.model_validate_json(spec.read_text())).model_dump_json())
    on_progress(0.5)
    subprocess.run(
        [
            ffmpeg_exe(),
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:s=320x180:r=30:d={duration}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(out),
        ],
        check=True,
    )
    on_progress(1.0)


@pytest.fixture
def brief() -> Brief:
    return Brief.model_validate(yaml.safe_load((REPO_ROOT / "examples/briefs/low.yaml").read_text()))


def words(n: int, prefix: str = "") -> str:
    return " ".join([*prefix.split(), *(["word"] * (n - len(prefix.split())))])


def beat_notes(brief: Brief, beats: int | None = None) -> list[tuple[str, int | None]]:
    """(role, key-point note) for each beat, as many beats as the video needs: a hook, a problem when there is room,
    one beat per note, more feature beats that develop them, and the call to action."""
    from reelhive.nodes.timing_node import beats_for

    count = beats or beats_for(brief)
    problem = [("problem", None)] if count >= len(brief.features) + 3 else []
    told = [("feature", i) for i in range(1, len(brief.features) + 1)]
    extra = [("feature", None)] * (count - 2 - len(problem) - len(told))
    return [("hook", None), *problem, *told, *extra, ("cta", None)]


def make_script(brief: Brief, total_words: int | None = None, drop: int | None = None) -> dict[str, Any]:
    """One beat per shot (note numbers in `covers`), hitting the word target; `drop` leaves that note untold."""
    from reelhive.nodes.timing_node import target_words

    notes = beat_notes(brief)
    per = -(-(total_words or target_words(brief)) // len(notes))
    beats = [
        {"role": role, "narration": words(per), "covers": [note] if note and note != drop else []}
        for role, note in notes
    ]
    return {"title": "CostHive launch", "beats": beats}


def make_plan(
    brief: Brief, drop_feature: int | None = None, narration: list[str] | None = None, beats: int | None = None
) -> dict[str, Any]:
    scenes: list[dict[str, Any]] = []
    for n, (role, note) in enumerate(beat_notes(brief, beats or (len(narration) if narration else None)), start=1):
        if role == "hook":
            scenes.append({"template": "hook", "headline": "Cloud bills grow silently", "secondary": "Find the waste"})
        elif role == "problem":
            scenes.append({"template": "hook", "headline": "Nobody owns the waste"})
        elif role == "cta":
            scenes.append(
                {
                    "template": "cta",
                    "headline": "Try CostHive free on GitHub",
                    "secondary": "github.com/d2k-klin/costhive",
                }
            )
        else:
            text = brief.features[note - 1] if note else f"Point {n}"
            scenes.append(
                {
                    "template": "feature-card",
                    "label": f"{n:02d}",
                    "headline": text[:40],
                    "secondary": text,
                    "covers": [] if note is None or note == drop_feature else [note],
                }
            )
    if narration:
        for s, line in zip(scenes, narration, strict=True):
            s["narration"] = line
    return {"intro": {"title": "CostHive", "tagline": "Find and fix cloud waste"}, "scenes": scenes}


VERDICT_PASS = {"hook": 4, "clarity": 4, "audience_fit": 5, "storyline": 4, "cta": 4, "passed": True, "reasons": []}


@pytest.fixture
def config(tmp_path: Path) -> Config:
    return Config(runs_dir=tmp_path / "runs")


def pdf(text: str) -> bytes:
    """A one-page 16:9 PDF with one line of text, xref offsets included."""
    stream = f"BT /F1 32 Tf 72 300 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 960 540] /Contents 4 0 R"
        b" /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (number, body)
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    return bytes(out)
