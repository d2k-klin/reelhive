"""What makes an eval run cheap: no Kokoro, no render, no paid images, no internet for screenshots."""

from __future__ import annotations

import functools
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np
import soundfile as sf
import yaml
from PIL import Image

from reelhive.nodes.timing_node import SPEECH_WPM
from reelhive.schemas.brief import Brief

DATASET = Path(__file__).parent / "datasets"
KOKORO_WPS = SPEECH_WPM / 60


class EstimateTTS:
    """Silence as long as Kokoro would take to say the text, so timing and pace metrics stay realistic."""

    def synth(self, text: str, out: Path, gender: str, accent: str, speed: float) -> float:
        seconds = max(0.5, len(text.split()) / KOKORO_WPS / speed)
        sf.write(out, np.zeros(int(seconds * 24000), dtype=np.float32), 24000)
        return seconds


class PromptRecorder:
    """An ImageGenerator that records each prompt and writes a placeholder instead of paying for an image."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate(self, prompt: str, size: str, output: Path) -> dict:
        self.prompts.append(prompt)
        width, height = (int(n) for n in size.split("x"))
        Image.new("RGB", (width, height), "#64748b").save(output)
        return {"images": 1, "placeholder": True}


@contextmanager
def serve_site(root: Path = DATASET / "site") -> Iterator[str]:
    """Serve the fixture site on 127.0.0.1 for screenshot briefs."""

    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *_: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(root)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def load_set(name: str, site: str, dataset: Path = DATASET) -> dict[str, Brief]:
    """Briefs of one set, with ${SITE} and ${DATASET} filled in, validated like any user brief."""
    names = yaml.safe_load((dataset / "sets.yaml").read_text())[name]
    briefs = {}
    for brief_name in names:
        text = (dataset / "briefs" / f"{brief_name}.yaml").read_text()
        text = text.replace("${SITE}", site).replace("${DATASET}", str(dataset.resolve()))
        briefs[brief_name] = Brief.model_validate(yaml.safe_load(text))
    return briefs
