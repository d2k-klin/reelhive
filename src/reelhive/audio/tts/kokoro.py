from __future__ import annotations

from pathlib import Path
from typing import Any

from reelhive.audio.tts.base import Speech, estimate_words
from reelhive.schemas.scene_spec import Word

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

    def synth(self, text: str, out: Path, gender: str, accent: str, speed: float) -> Speech:
        import numpy as np
        import soundfile as sf

        chunks, words, offset = [], [], 0.0
        for result in self._pipeline(accent)(text, voice=VOICES[(gender, accent)], speed=speed):
            if result.audio is None:
                continue
            audio = result.audio.numpy()
            seconds = len(audio) / SAMPLE_RATE
            words += chunk_words(result.tokens or [], result.graphemes, offset, seconds)
            chunks.append(audio)
            offset += seconds
        audio = np.concatenate(chunks) if chunks else np.zeros(SAMPLE_RATE // 2, dtype=np.float32)
        sf.write(out, audio, SAMPLE_RATE)
        return Speech(len(audio) / SAMPLE_RATE, words)


def chunk_words(tokens: list[Any], text: str, offset: float, seconds: float) -> list[Word]:
    """Kokoro's per-token timestamps for one chunk, shifted by where the chunk starts in the scene's audio.
    Punctuation joins the word before it; a chunk without timestamps is estimated from its text."""
    words: list[Word] = []
    for token in tokens:
        if token.start_ts is not None and token.end_ts is not None and any(c.isalnum() for c in token.text):
            words.append(
                Word(text=token.text, start=round(offset + token.start_ts, 3), end=round(offset + token.end_ts, 3))
            )
        elif words and token.text.strip() and not any(c.isalnum() for c in token.text):
            words[-1].text += token.text.strip()
    return words or estimate_words(text, offset, seconds)
