from __future__ import annotations

from pathlib import Path
from typing import Any

SAMPLE_RATE = 24000
VOICES = {
    ("female", "us"): "af_heart",
    ("female", "uk"): "bf_emma",
    ("male", "us"): "am_michael",
    ("male", "uk"): "bm_george",
}


class KokoroTTS:
    """Kokoro-82M on CPU (or Apple Silicon / CUDA when torch finds them). Imported lazily: torch is heavy."""

    def __init__(self) -> None:
        self._pipelines: dict[str, Any] = {}

    def _pipeline(self, accent: str) -> Any:
        lang = "b" if accent == "uk" else "a"
        if lang not in self._pipelines:
            from kokoro import KPipeline

            self._pipelines[lang] = KPipeline(lang_code=lang, repo_id="hexgrad/Kokoro-82M")
        return self._pipelines[lang]

    def synth(self, text: str, out: Path, gender: str, accent: str, speed: float) -> float:
        import numpy as np
        import soundfile as sf

        chunks = [
            audio.numpy()
            for _, _, audio in self._pipeline(accent)(text, voice=VOICES[(gender, accent)], speed=speed)
            if audio is not None
        ]
        audio = np.concatenate(chunks) if chunks else np.zeros(SAMPLE_RATE // 2, dtype=np.float32)
        sf.write(out, audio, SAMPLE_RATE)
        return len(audio) / SAMPLE_RATE
