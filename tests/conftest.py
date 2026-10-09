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
from reelhive.config import REPO_ROOT, Config
from reelhive.schemas.brief import Brief

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

    def synth(self, text: str, out: Path, gender: str, accent: str, speed: float) -> float:
        self.calls.append(text)
        seconds = len(text.split()) / WORDS_PER_SECOND / speed
        sf.write(out, np.zeros(int(seconds * 24000), dtype=np.float32), 24000)
        return seconds


def stub_renderer(spec: Path, out: Path, on_progress: Callable[[float], None]) -> None:
    """A black video as long as the spec, made by ffmpeg instead of Revideo."""
    duration = json.loads(spec.read_text())["duration"]
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
    return Brief.model_validate(yaml.safe_load((REPO_ROOT / "examples/briefs/small.yaml").read_text()))


def words(n: int, prefix: str = "") -> str:
    return " ".join([*prefix.split(), *(["word"] * (n - len(prefix.split())))])


def make_script(brief: Brief, total_words: int = 141, drop: int | None = None) -> dict[str, Any]:
    """One beat per key point (note numbers in `covers`); `drop` leaves that note untold."""
    roles = ["hook", "problem", *(["feature"] * len(brief.features)), "cta"]
    per = total_words // len(roles)
    beats = []
    for i, role in enumerate(roles):
        note = i - 1 if role == "feature" else None
        beats.append({"role": role, "narration": words(per), "covers": [note] if note and note != drop else []})
    return {"title": "CostHive launch", "beats": beats}


def make_plan(brief: Brief, drop_feature: int | None = None, narration: list[str] | None = None) -> dict[str, Any]:
    scenes: list[dict[str, Any]] = [
        {"template": "hook", "headline": "Cloud bills grow silently", "secondary": "Find the waste in minutes"},
        {"template": "hook", "headline": "Nobody owns the waste"},
    ]
    for i, f in enumerate(brief.features, start=1):
        scenes.append(
            {
                "template": "feature-card",
                "label": f"0{i}",
                "headline": f[:40],
                "secondary": f,
                "covers": [] if i == drop_feature else [i],
            }
        )
    scenes.append(
        {"template": "cta", "headline": "Try CostHive free on GitHub", "secondary": "github.com/d2k-klin/costhive"}
    )
    if narration:
        for s, n in zip(scenes, narration, strict=True):
            s["narration"] = n
    return {"scenes": scenes}


VERDICT_PASS = {"hook": 4, "clarity": 4, "audience_fit": 5, "storyline": 4, "cta": 4, "passed": True, "reasons": []}


@pytest.fixture
def config(tmp_path: Path) -> Config:
    return Config(runs_dir=tmp_path / "runs")
