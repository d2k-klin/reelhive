import stat

import numpy as np
import pytest
import soundfile as sf

from reelhive.audio import mixer
from reelhive.render import bridge
from reelhive.schemas.scene_spec import CREDIT_TEXT, HookScene, HookText, SceneSpec


def test_mix_args_duck_the_music_under_the_voice(tmp_path):
    args = mixer.mix_args(tmp_path / "n.wav", tmp_path / "m.mp3", 60.0, tmp_path / "mix.wav")
    graph = args[args.index("-filter_complex") + 1]
    assert "sidechaincompress" in graph and "[music][key]" in graph
    assert args[:2] == ["-stream_loop", "-1"]  # short tracks loop under long videos
    assert "afade=t=out:st=58.000" in graph
    assert "-filter_complex" not in mixer.mix_args(tmp_path / "n.wav", None, 60.0, tmp_path / "mix.wav")


def test_mux_always_writes_the_credit_metadata(tmp_path):
    args = mixer.mux_args(tmp_path / "v.mp4", tmp_path / "a.wav", tmp_path / "out.mp4")
    assert f"comment={CREDIT_TEXT}" in args


def test_narration_track_places_voice_at_scene_start(tmp_path):
    (tmp_path / "audio").mkdir()
    sf.write(tmp_path / "audio/scene_02.wav", np.ones(2400, dtype=np.float32) * 0.5, 24000)
    spec = SceneSpec(
        duration=4.0,
        scenes=[
            HookScene(index=1, narration="a", text=HookText(headline="h"), start=0.0, duration=2.0),
            HookScene(
                index=2, narration="b", text=HookText(headline="h"), start=2.0, duration=2.0, audio="audio/scene_02.wav"
            ),
        ],
    )
    track, sr = sf.read(mixer.narration_track(tmp_path, spec, tmp_path / "n.wav"))
    at = int((2.0 + 0.3) * sr)
    assert len(track) == 4 * sr
    assert track[at - 10] == 0 and track[at + 10] == pytest.approx(0.5, abs=1e-3)


def test_ffmpeg_errors_surface(tmp_path):
    with pytest.raises(RuntimeError, match="ffmpeg failed"):
        mixer.mux(tmp_path / "missing.mp4", tmp_path / "missing.wav", tmp_path / "out.mp4")


def fake_repo(tmp_path, monkeypatch, script: str):
    tsx = tmp_path / "node_modules/.bin/tsx"
    tsx.parent.mkdir(parents=True)
    tsx.write_text("#!/bin/sh\n" + script)
    tsx.chmod(tsx.stat().st_mode | stat.S_IEXEC)
    (tmp_path / "renderer").mkdir()
    monkeypatch.setattr(bridge, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(bridge, "RENDERER_DIR", tmp_path / "renderer")


def test_bridge_streams_progress(tmp_path, monkeypatch):
    fake_repo(tmp_path, monkeypatch, 'echo "progress 0.250"\necho "vite ready"\necho "progress 1.000"\ntouch "$3"\n')
    seen = []
    bridge.render(tmp_path / "spec.json", tmp_path / "out.mp4", seen.append)
    assert seen == [0.25, 1.0]


def test_bridge_reports_renderer_failure_and_missing_deps(tmp_path, monkeypatch):
    monkeypatch.setattr(bridge, "REPO_ROOT", tmp_path)
    with pytest.raises(bridge.RenderError, match="make setup"):
        bridge.render(tmp_path / "s.json", tmp_path / "o.mp4", print)
    fake_repo(tmp_path / "r", monkeypatch, 'echo "Error: boom"\nexit 1\n')
    with pytest.raises(bridge.RenderError, match="boom"):
        bridge.render(tmp_path / "s.json", tmp_path / "o.mp4", print)


def test_bundled_binaries_get_their_execute_bit_back(tmp_path):
    # `npm ci --ignore-scripts` skips @ffprobe-installer's `chmod u+x`; rendering then died on spawn EACCES.
    probe_bin = tmp_path / "node_modules/@ffprobe-installer/darwin-arm64/ffprobe"
    ffmpeg_bin = tmp_path / "node_modules/@ffmpeg-installer/darwin-arm64/ffmpeg"
    for b in (probe_bin, ffmpeg_bin):
        b.parent.mkdir(parents=True)
        b.write_text("#!/bin/sh\n")
    probe_bin.chmod(0o644)
    ffmpeg_bin.chmod(0o755)
    assert bridge.ensure_executable(tmp_path) == [probe_bin]
    assert probe_bin.stat().st_mode & 0o100
    assert bridge.ensure_executable(tmp_path) == []  # idempotent


def test_renderer_failure_explains_permission_errors(tmp_path, monkeypatch):
    fake_repo(tmp_path, monkeypatch, 'echo "Error: spawn /x/ffprobe EACCES"\nexit 1\n')
    with pytest.raises(bridge.RenderError, match="npm rebuild"):
        bridge.render(tmp_path / "s.json", tmp_path / "o.mp4", print)
