import json

import pytest
from conftest import VERDICT_PASS, FakeModel, StubTTS, make_plan, make_script, stub_renderer

from reelhive.core.service import Service
from reelhive.schemas.brief import Brief


@pytest.mark.parametrize("format,size", [("9:16", (1080, 1920)), ("1:1", (1080, 1080))])
def test_medium_pauses_and_resumes_edited_script(config, brief, format, size):
    brief = Brief.model_validate(
        {
            **brief.model_dump(),
            "level": "medium",
            "format": format,
            "brand": {"colors": ["#123456"]},
            "voice": {"accent": "uk"},
        }
    )
    draft_model = FakeModel({"Script": make_script(brief)})
    tts = StubTTS()
    events = []
    result = Service(config, {"strong": draft_model}, tts, stub_renderer).run(brief, events.append)
    assert result.status == "awaiting_script" and not tts.calls
    assert draft_model.calls == ["Script"]
    script_path = result.run_dir / "script.json"
    script = json.loads(script_path.read_text())
    script["beats"][0]["narration"] = script["beats"][0]["narration"].replace("word", "edited", 1)
    script_path.write_text(json.dumps(script))
    production = FakeModel(
        {
            "ScenePlan": make_plan(brief),
            "MusicChoice": {"mood": "tech", "bpm": 110, "reason": "fits"},
            "Verdict": VERDICT_PASS,
        }
    )
    svc = Service(config, {"strong": production, "fast": production}, tts, stub_renderer)
    final = svc.approve(result.run_dir, events.append)
    assert final.status == "done" and tts.calls[0].startswith("edited")
    assert "Script" not in production.calls
    spec = json.loads((final.run_dir / "spec.json").read_text())
    assert (spec["width"], spec["height"]) == size and spec["theme"]["accent"] == "#123456"
    assert json.loads((final.run_dir / "status.json").read_text())["status"] == "done"
    with pytest.raises(ValueError, match="not awaiting"):
        svc.approve(result.run_dir)


def test_invalid_approval_leaves_run_editable(config, brief):
    brief.level = "medium"
    model = FakeModel({"Script": make_script(brief)})
    svc = Service(config, {"strong": model}, StubTTS(), stub_renderer)
    result = svc.run(brief)
    (result.run_dir / "script.json").write_text('{"beats": []}')
    with pytest.raises(ValueError):
        svc.approve(result.run_dir)
    assert json.loads((result.run_dir / "status.json").read_text())["status"] == "awaiting_script"
    assert not (result.run_dir / ".production.lock").exists()


def test_concurrent_approval_is_refused_without_touching_the_lock(config, brief):
    brief.level = "medium"
    svc = Service(config, {"strong": FakeModel({"Script": make_script(brief)})}, StubTTS(), stub_renderer)
    result = svc.run(brief)
    (result.run_dir / ".production.lock").touch()  # another terminal is producing this run
    with pytest.raises(ValueError, match="already being produced"):
        svc.approve(result.run_dir)
    assert (result.run_dir / ".production.lock").exists()
