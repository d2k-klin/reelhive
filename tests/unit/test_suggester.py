"""M6 quick actions: suggestions per beat or scene, cached per version, logged as events."""

import json

import pytest
from conftest import FakeModel, StubTTS, make_script, stub_renderer
from pydantic import ValidationError

from reelhive.agents.suggester import Suggestions, target_json
from reelhive.config import Config
from reelhive.core.events import replay
from reelhive.core.service import Service
from reelhive.providers.factory import ProviderError
from reelhive.schemas.script import Script

THREE = {
    "suggestions": [
        {"label": "Punchier hook", "instruction": "Open with the cost number, keep the second sentence as is."},
        {"label": "Shorten by ~2s", "instruction": "Cut about five spoken words; keep the product name."},
        {"label": "Simpler wording", "instruction": "Replace jargon with everyday words for the audience."},
    ]
}


def paused_run(config, brief):
    brief.level = "medium"
    result = Service(config, {"strong": FakeModel({"Script": make_script(brief)})}, StubTTS(), stub_renderer).run(brief)
    assert result.status == "awaiting_script"
    return result.run_dir


def test_suggestions_are_validated():
    Suggestions.model_validate(THREE)
    with pytest.raises(ValidationError, match="at least 3"):
        Suggestions.model_validate({"suggestions": THREE["suggestions"][:2]})
    with pytest.raises(ValidationError, match="distinct"):
        Suggestions.model_validate({"suggestions": [THREE["suggestions"][0]] * 3})
    with pytest.raises(ValidationError):
        Suggestions.model_validate({"suggestions": [{**s, "label": "x" * 40} for s in THREE["suggestions"]]})


def test_beat_suggestions_are_cached_per_version_and_logged(config, brief):
    run_dir = paused_run(config, brief)
    model = FakeModel({"Suggestions": [THREE, THREE]})
    svc = Service(config, {"fast": model})
    seen = []

    first = svc.suggest(run_dir, "beat", 1, seen.append)
    again = svc.suggest(run_dir, "beat", 1)
    assert [s.label for s in first.suggestions] == [s.label for s in again.suggestions]
    assert model.calls == ["Suggestions"]  # second call came from the cache
    assert len(list((run_dir / "suggestions").glob("beat_01_*.json"))) == 1

    script = json.loads((run_dir / "script.json").read_text())  # the user edits the beat: a new version
    script["beats"][0]["narration"] += " Edited."
    (run_dir / "script.json").write_text(json.dumps(script))
    svc.suggest(run_dir, "beat", 1)
    assert model.calls == ["Suggestions", "Suggestions"]

    offered = [e.data for e in replay(run_dir / "run.log.jsonl") if e.type == "suggestion.offered"]
    assert [o["cached"] for o in offered] == [False, True, False]
    assert offered[0]["suggestions"][0]["label"] == "Punchier hook" and seen[0].data["index"] == 1


def test_targets_must_exist(config, brief):
    run_dir = paused_run(config, brief)
    script = Script.model_validate_json((run_dir / "script.json").read_text())
    with pytest.raises(ValueError, match="beat 99 does not exist"):
        target_json("beat", 99, script, None)
    with pytest.raises(ValueError, match="no scene spec yet"):
        Service(config, {"fast": FakeModel({})}).suggest(run_dir, "scene", 1)


def test_copilot_suggestions_are_a_follow_up(config, brief):
    run_dir = paused_run(config, brief)
    with pytest.raises(ProviderError, match="follow-up"):
        Service(Config(provider="copilot", runs_dir=config.runs_dir)).suggest(run_dir, "beat", 1)


def test_scene_suggestions_use_the_spec(config, brief):
    from reelhive.schemas.scene_spec import HookScene, HookText, SceneSpec

    run_dir = paused_run(config, brief)
    spec = SceneSpec(scenes=[HookScene(index=1, narration="Bills grow.", text=HookText(headline="Bills grow"))])
    (run_dir / "spec.json").write_text(spec.model_dump_json())
    result = Service(config, {"fast": FakeModel({"Suggestions": THREE})}).suggest(run_dir, "scene", 1)
    assert len(result.suggestions) == 3
    assert list((run_dir / "suggestions").glob("scene_01_*.json"))
