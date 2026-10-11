"""Captions follow the recorded voice: word timings from the TTS reach the spec, shifted to the scene clock."""

from types import SimpleNamespace

import pytest

from reelhive.audio.tts.base import estimate_words
from reelhive.audio.tts.kokoro import chunk_words
from reelhive.core.context import RunContext
from reelhive.core.events import EventBus
from reelhive.nodes.timing_node import LEAD, apply_timing
from reelhive.schemas.scene_spec import HookScene, HookText, SceneSpec, Word


def token(text, start=None, end=None):
    return SimpleNamespace(text=text, start_ts=start, end_ts=end)


def test_kokoro_timestamps_are_shifted_by_the_chunk_and_keep_their_punctuation():
    words = chunk_words(
        [token("Try", 0.1, 0.3), token("it", 0.35, 0.5), token(","), token("today", 0.6, 0.9)], "", 2.0, 1.0
    )
    assert [(w.text, w.start, w.end) for w in words] == [("Try", 2.1, 2.3), ("it,", 2.35, 2.5), ("today", 2.6, 2.9)]


def test_a_chunk_without_timestamps_is_estimated_from_its_text():
    words = chunk_words([token("Hello"), token("world")], "Hello world", 1.0, 2.0)
    assert (
        [w.text for w in words] == ["Hello", "world"] and words[0].start == 1.0 and words[-1].end == pytest.approx(3.0)
    )


def test_estimated_words_fill_the_audio_in_order():
    words = estimate_words("A longer sentence here.", 0.0, 4.0)
    assert [w.text for w in words] == ["A", "longer", "sentence", "here."]
    assert words[0].end <= words[1].start + 1e-6 and words[-1].end == pytest.approx(4.0)


def test_timing_puts_the_words_on_the_scene_clock_and_follows_the_brief(brief):
    brief.captions = True
    spec = SceneSpec(scenes=[HookScene(index=1, narration="Go now", text=HookText(headline="h"))])
    apply_timing(
        spec,
        {1: ("Go now", 1.0)},
        brief,
        {1: [Word(text="Go", start=0.0, end=0.4), Word(text="now", start=0.5, end=0.9)]},
    )
    assert spec.captions and [(w.start, w.end) for w in spec.scenes[0].words] == [
        (LEAD, LEAD + 0.4),
        (LEAD + 0.5, LEAD + 0.9),
    ]


def test_word_timings_survive_a_checkpoint(tmp_path, brief):
    ctx = RunContext(tmp_path, brief, EventBus(), {}, None, None)
    ctx.words = {2: [Word(text="Hi", start=0.1, end=0.3)]}
    ctx.checkpoint()
    restored = RunContext(tmp_path, brief, EventBus(), {}, None, None)
    restored.restore()
    assert restored.words == ctx.words
