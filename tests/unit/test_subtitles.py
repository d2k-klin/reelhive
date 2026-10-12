"""Subtitle files carry the same phrases the renderer burns in, on the video clock."""

import re

from reelhive.config import REPO_ROOT
from reelhive.render import subtitles
from reelhive.schemas.scene_spec import HookScene, HookText, SceneSpec, Word


def scene(index, start, words):
    return HookScene(
        index=index,
        narration=" ".join(t for t, _, _ in words),
        text=HookText(headline="h"),
        start=start,
        duration=5,
        words=[Word(text=t, start=s, end=e) for t, s, e in words],
    )


def spec():
    return SceneSpec(
        duration=10,
        scenes=[
            scene(1, 0.0, [("Cloud", 0.3, 0.6), ("bills", 0.6, 0.9), ("grow,", 0.9, 1.2), ("silently", 1.3, 1.8)]),
            scene(
                2,
                5.0,
                [("One", 0.3, 0.5), ("two", 0.5, 0.7), ("three", 0.7, 0.9), ("four", 0.9, 1.1), ("five", 1.1, 1.3)],
            ),
        ],
    )


def test_phrases_break_after_punctuation_and_at_four_words_on_the_video_clock():
    cues = subtitles.cues(spec())
    assert [c.text for c in cues] == ["Cloud bills grow,", "silently", "One two three four", "five"]
    assert cues[0].start == 0.3 and cues[0].end == 1.3  # lingers 0.4 s, but gives way to the next phrase
    assert cues[1].end == 2.2 and cues[2].start == 5.3


def test_srt_and_vtt_formats(tmp_path):
    cues = subtitles.cues(spec())
    assert subtitles.srt(cues).startswith("1\n00:00:00,300 --> 00:00:01,300\nCloud bills grow,\n\n2\n")
    assert subtitles.vtt(cues).startswith("WEBVTT\n\n00:00:00.300 --> 00:00:01.300\nCloud bills grow,\n")
    written = subtitles.write(spec(), tmp_path / "video.mp4")
    assert [p.name for p in written] == ["video.srt", "video.vtt"]


def test_no_voice_means_no_subtitles_and_removes_stale_ones(tmp_path):
    (tmp_path / "video.srt").write_text("old")
    assert subtitles.write(spec(), tmp_path / "video.mp4", voiced=False) == []
    assert not (tmp_path / "video.srt").exists()


def test_phrasing_matches_the_burned_in_captions():
    source = (REPO_ROOT / "renderer/src/components/captions.tsx").read_text()
    constants = dict(re.findall(r"const (MAX_WORDS|MAX_CHARS|LINGER) = ([\d.]+);", source))
    assert float(constants["MAX_WORDS"]) == subtitles.MAX_WORDS
    assert float(constants["MAX_CHARS"]) == subtitles.MAX_CHARS
    assert float(constants["LINGER"]) == subtitles.LINGER
    assert "/[.,!?;:]$/" in source and subtitles.BREAK.pattern == "[.,!?;:]$"


def test_a_subtitle_track_never_shortens_the_video(tmp_path):
    """The last caption ends with the last word; the closing frame and credit run on after it."""
    import subprocess

    from reelhive.audio import mixer

    ffmpeg = mixer.ffmpeg_exe()
    video, audio = tmp_path / "silent.mp4", tmp_path / "mix.wav"
    subprocess.run(
        [
            ffmpeg,
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=320x180:r=30:d=6",
            "-pix_fmt",
            "yuv420p",
            str(video),
        ],
        check=True,
    )
    subprocess.run(
        [ffmpeg, "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "6", str(audio)],
        check=True,
    )
    srt = tmp_path / "video.srt"
    srt.write_text("1\n00:00:00,500 --> 00:00:02,000\nHello\n")
    out = mixer.mux(video, audio, tmp_path / "video.mp4", srt, duration=6.0)
    info = mixer.probe(out)
    assert info["has_subtitles"] and abs(info["duration"] - 6.0) < 0.1
