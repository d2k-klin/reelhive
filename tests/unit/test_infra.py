"""Events, config, levels, provider factory, music library, doctor."""

import json

import pytest

from reelhive.audio.music_library import MOODS, MUSIC_DIR, load_manifest, pick_track
from reelhive.config import Config, load_config
from reelhive.core.events import EventBus, replay
from reelhive.doctor import run_checks
from reelhive.levels import LEVELS
from reelhive.providers.factory import ProviderError, build_models


def test_events_fan_out_log_and_replay(tmp_path):
    seen = []
    bus = EventBus(tmp_path / "run.log.jsonl")
    bus.subscribe(seen.append)
    bus.emit("node.started", node="script")
    bus.emit("node.finished", node="script", status="completed", seconds=1.0, tokens=10)
    with pytest.raises(ValueError):
        bus.emit("node.exploded", node="x")
    assert [e.type for e in seen] == ["node.started", "node.finished"]
    assert [(e.type, e.data) for e in replay(tmp_path / "run.log.jsonl")] == [(e.type, e.data) for e in seen]


def test_config_defaults_and_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert load_config().models["claude"].strong == "claude-sonnet-5-5"
    (tmp_path / "config.yaml").write_text("models:\n  claude: {strong: a, fast: b}\nruns_dir: out\n")
    cfg = load_config()
    assert (cfg.models["claude"].fast, str(cfg.runs_dir)) == ("b", "out")


def test_small_level_pins_accent_and_speed(brief):
    voice = brief.voice.model_copy(update={"accent": "uk", "speed": 1.2})
    filled = LEVELS["low"].defaults(brief.model_copy(update={"voice": voice}))
    assert (filled["voice"].accent, filled["voice"].speed, filled["voice"].gender) == ("us", 1.0, "female")
    assert LEVELS["low"].approval_stops == ()


def test_factory_builds_claude_tiers():
    models = build_models(Config())
    assert {t: m.get_config()["model_id"] for t, m in models.items()} == {
        "strong": "claude-sonnet-5-5",
        "fast": "claude-haiku-5-5",
    }


def test_factory_rejects_unavailable_providers():
    with pytest.raises(ProviderError, match="models.ollama"):
        build_models(Config(provider="ollama"))
    with pytest.raises(ProviderError, match="models.claude"):
        build_models(Config(models={}))


def test_music_manifest_is_cc0_and_complete():
    tracks = load_manifest()
    assert {t["mood"] for t in tracks} == set(MOODS)
    for t in tracks:
        assert t["license"] == "CC0-1.0" and t["source"]
        assert (MUSIC_DIR / t["file"]).exists()


def test_pick_track_prefers_mood_then_nearest_bpm():
    assert pick_track("calm", 150)["mood"] == "calm"
    assert pick_track("polka", 118)["bpm"] == 120
    assert pick_track("tech", 110)["file"].endswith("tech-110.mp3")


def test_doctor_reports_credit_state(monkeypatch):
    monkeypatch.setenv("REELHIVE_DISABLE_CREDIT", "true")
    credit = {r.name: r for r in run_checks()}["credit"]
    assert "disabled" in credit.detail and not credit.required
    monkeypatch.delenv("REELHIVE_DISABLE_CREDIT")
    assert "on" in {r.name: r for r in run_checks()}["credit"].detail


def test_manifest_json_is_well_formed():
    assert json.loads((MUSIC_DIR / "manifest.json").read_text())["tracks"]
