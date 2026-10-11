"""Real Kokoro, real Revideo, real ffmpeg: one short scene (pytest -m slow)."""

import pytest

from reelhive.audio import mixer
from reelhive.audio.music_library import pick_track
from reelhive.audio.tts.kokoro import KokoroTTS
from reelhive.nodes.timing_node import LEAD, TAIL
from reelhive.render.bridge import render
from reelhive.schemas.scene_spec import CREDIT_TEXT, Credit, CtaScene, CtaText, SceneSpec

pytestmark = pytest.mark.slow


def test_one_scene_renders_with_voice_music_and_credit(tmp_path):
    (tmp_path / "audio").mkdir()
    speech = KokoroTTS().synth("Try ReelHive today.", tmp_path / "audio/scene_01.wav", "female", "us", 1.0)
    seconds = speech.seconds
    assert 0.5 < seconds < 4
    # Kokoro's own timestamps: every word, in order, inside the audio, punctuation joined to its word.
    assert " ".join(w.text for w in speech.words) == "Try ReelHive today."
    starts = [w.start for w in speech.words]
    assert starts == sorted(starts) and speech.words[-1].end <= seconds

    duration = round(seconds + LEAD + TAIL, 2)
    spec = SceneSpec(
        duration=duration + 1.5,
        scenes=[
            CtaScene(
                index=1,
                narration="Try ReelHive today.",
                text=CtaText(headline="Try ReelHive today."),
                audio="audio/scene_01.wav",
                start=0,
                duration=duration,
                words=[w.model_copy(update={"start": LEAD + w.start, "end": LEAD + w.end}) for w in speech.words],
            )
        ],
        captions=True,
        credit=Credit(mode="end", duration=1.5),
        music=pick_track("upbeat", 120)["file"],
    )
    (tmp_path / "spec.json").write_text(spec.model_dump_json())
    progress: list[float] = []
    render(tmp_path / "spec.json", tmp_path / "silent.mp4", progress.append)
    video = mixer.mux(tmp_path / "silent.mp4", mixer.mix(tmp_path, spec), tmp_path / "video.mp4")

    info = mixer.probe(video)
    assert progress and progress[-1] == pytest.approx(1.0)
    assert info["duration"] == pytest.approx(spec.duration, abs=0.2)
    assert (info["width"], info["height"]) == (1920, 1080)
    assert info["has_audio"] and info["comment"] == CREDIT_TEXT
