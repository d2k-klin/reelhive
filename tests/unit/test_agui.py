"""M6 backend: the AG-UI endpoint, apply with a suggestion, undo. Fake model, no network."""

import json

import pytest
from conftest import VERDICT_PASS, FakeModel, StubTTS, make_plan, make_script, stub_renderer
from fastapi.testclient import TestClient

from reelhive.config import Config
from reelhive.core.events import replay
from reelhive.core.service import Service
from reelhive.core.workspace import Workspace
from reelhive.server.app import create_app

THREE = {
    "suggestions": [
        {"label": "Punchier hook", "instruction": "Open with the cost number, keep the second sentence."},
        {"label": "Shorten by ~2s", "instruction": "Cut about five spoken words; keep the product name."},
        {"label": "Simpler wording", "instruction": "Replace jargon with everyday words for the audience."},
    ]
}
TOKEN = "test-token"
ORIGIN = "http://127.0.0.1"


def run_input(state, messages=None):
    return {
        "threadId": "t1",
        "runId": "r1",
        "state": state,
        "messages": messages or [],
        "tools": [],
        "context": [],
        "forwardedProps": {},
    }


@pytest.fixture
def studio(tmp_path, brief):
    """A medium run paused at the script, served by the real app with fake models."""
    config = Config(runs_dir=tmp_path / "runs")
    brief.level = "medium"
    first = Service(config, {"strong": FakeModel({"Script": make_script(brief)})}, StubTTS(), stub_renderer).run(brief)
    model = FakeModel({"Suggestions": [THREE] * 5, "Script": [make_script(brief)] * 3})
    ws = Workspace(
        config, service_factory=lambda c: Service(c, {"strong": model, "fast": model}, StubTTS(), stub_renderer)
    )
    client = TestClient(create_app(config, token=TOKEN, workspace=ws), base_url="http://127.0.0.1")
    yield client, first.run_dir, model, ws
    ws.close()


def post(client, path, body, **headers):
    return client.post(path, json=body, headers={"Authorization": f"Bearer {TOKEN}", "Origin": ORIGIN, **headers})


def sse(response):
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]


def test_agui_streams_one_validated_tool_call_and_caches(studio):
    client, run_dir, model, _ = studio
    state = {"run_id": run_dir.name, "target": "beat", "index": 1}
    events = sse(post(client, "/api/agui/suggest", run_input(state)))
    assert [e["type"] for e in events] == [
        "RUN_STARTED",
        "TOOL_CALL_START",
        "TOOL_CALL_ARGS",
        "TOOL_CALL_END",
        "RUN_FINISHED",
    ]
    assert events[1]["toolCallName"] == "propose_suggestions"
    assert [s["label"] for s in json.loads(events[2]["delta"])["suggestions"]][0] == "Punchier hook"
    post(client, "/api/agui/suggest", run_input(state))
    assert model.calls.count("Suggestions") == 1  # same beat version: cached
    post(client, "/api/agui/suggest", run_input({**state, "fresh": True}))
    assert model.calls.count("Suggestions") == 2  # "More ideas"
    offered = [e.data["cached"] for e in replay(run_dir / "run.log.jsonl") if e.type == "suggestion.offered"]
    assert offered == [False, True, False]


def test_agui_ends_quietly_after_the_tool_result_and_reports_bad_state(studio):
    client, run_dir, _, _ = studio
    tool_result = [{"id": "m1", "role": "tool", "content": "shown", "toolCallId": "c1"}]
    events = sse(post(client, "/api/agui/suggest", run_input({}, tool_result)))
    assert [e["type"] for e in events] == ["RUN_STARTED", "RUN_FINISHED"]
    events = sse(post(client, "/api/agui/suggest", run_input({"run_id": "../etc", "target": "beat", "index": 1})))
    assert events[-1]["type"] == "RUN_ERROR" and "invalid run id" in events[-1]["message"]
    events = sse(post(client, "/api/agui/suggest", run_input({"run_id": run_dir.name, "target": "beat", "index": 99})))
    assert events[-1]["type"] == "RUN_ERROR" and "does not exist" in events[-1]["message"]


def test_agui_endpoint_has_the_same_security_as_every_route(studio):
    client, run_dir, model, _ = studio
    body = run_input({"run_id": run_dir.name, "target": "beat", "index": 1})
    assert client.post("/api/agui/suggest", json=body, headers={"Origin": ORIGIN}).status_code == 401
    assert post(client, "/api/agui/suggest", body, Origin="http://evil.example").status_code == 403
    assert post(client, "/api/agui/suggest", body, Host="evil.example").status_code == 403
    assert "Suggestions" not in model.calls


def test_apply_logs_the_suggestion_and_undo_restores_the_script(studio):
    client, run_dir, _, ws = studio
    original = json.loads((run_dir / "script.json").read_text())
    edited = {
        **original,
        "beats": [{**original["beats"][0], "narration": "Edited by the user."}, *original["beats"][1:]],
    }
    (run_dir / "script.json").write_text(json.dumps(edited))
    response = post(
        client,
        f"/api/runs/{run_dir.name}/script/regenerate",
        {"note": "Open with the cost number.", "suggestion": "Punchier hook", "beat": 1},
    )
    assert response.status_code == 202
    ws.jobs[run_dir.name].result(timeout=10)
    assert json.loads((run_dir / "script.json").read_text()) != edited
    assert post(client, f"/api/runs/{run_dir.name}/script/undo", {}).status_code == 200
    assert json.loads((run_dir / "script.json").read_text()) == edited
    assert post(client, f"/api/runs/{run_dir.name}/script/undo", {}).status_code == 422  # nothing left to undo
    log = replay(run_dir / "run.log.jsonl")
    applied = [e.data for e in log if e.type == "suggestion.applied"]
    restored = [e.data for e in log if e.type == "version.restored"]
    assert applied == [{"target": "beat", "index": 1, "label": "Punchier hook", "note": "Open with the cost number."}]
    assert restored == [{"target": "script", "index": None, "suggestion": "Punchier hook"}]


def test_scene_apply_and_undo_round_trip(tmp_path, brief):
    brief.level = "high"
    config = Config(runs_dir=tmp_path / "runs")
    one = {
        "scenes": [
            {
                "template": "feature-card",
                "label": "01",
                "headline": "Every region, fast",
                "secondary": "Short body.",
                "feature": brief.features[0],
            }
        ]
    }
    models = FakeModel(
        {
            "Script": make_script(brief),
            "ScenePlan": [make_plan(brief), one],
            "MusicChoice": {"mood": "tech", "bpm": 110, "reason": "x"},
            "Verdict": VERDICT_PASS,
        }
    )
    svc = Service(config, {"strong": models, "fast": models}, StubTTS(), stub_renderer)
    run_dir = svc.run(brief).run_dir
    svc.approve(run_dir)
    before = json.loads((run_dir / "spec.json").read_text())["scenes"][2]
    svc.regenerate_scene(run_dir, 3, "Shorter body.", suggestion="Shorten by ~2s")
    after = json.loads((run_dir / "spec.json").read_text())["scenes"][2]
    assert after["text"] != before["text"]
    svc.undo_scene(run_dir, 3)
    restored = json.loads((run_dir / "spec.json").read_text())["scenes"][2]
    assert restored["text"] == before["text"] and restored["narration"] == before["narration"]
    with pytest.raises(ValueError, match="nothing to undo"):
        svc.undo_scene(run_dir, 3)


def test_live_log_downloads_as_a_complete_snapshot(studio):
    client, run_dir, _, _ = studio
    response = client.get(f"/api/runs/{run_dir.name}/files/run.log.jsonl", headers={"Authorization": f"Bearer {TOKEN}"})
    assert response.status_code == 200
    assert response.content == (run_dir / "run.log.jsonl").read_bytes()


def test_low_level_start_runs_through_without_a_queue_race(tmp_path, brief):
    """The draft job queues production itself; its cleanup must not remove that entry (list.remove crash)."""
    import time

    config = Config(runs_dir=tmp_path / "runs")
    model = FakeModel(
        {
            "Script": make_script(brief),
            "ScenePlan": make_plan(brief),
            "MusicChoice": {"mood": "tech", "bpm": 110, "reason": "x"},
            "Verdict": VERDICT_PASS,
        }
    )
    ws = Workspace(
        config, service_factory=lambda c: Service(c, {"strong": model, "fast": model}, StubTTS(), stub_renderer)
    )
    try:
        ws.production.acquire()  # hold production so the draft job's cleanup runs first (the losing interleaving)
        view = ws.create(brief.model_copy(update={"level": "low"}))
        for _ in range(200):
            if json.loads((ws.path(view.id) / "status.json").read_text())["status"] == "queued":
                break
            time.sleep(0.05)
        time.sleep(0.3)  # let the draft job finish and clean up
        ws.production.release()
        for _ in range(200):
            status = json.loads((ws.path(view.id) / "status.json").read_text())
            if status["status"] in {"done", "failed", "stopped"}:
                break
            time.sleep(0.05)
        assert status["status"] == "done", status
    finally:
        ws.close()


def test_approving_a_stopped_run_rechecks_instead_of_replaying(tmp_path, brief):
    brief.level = "high"
    config = Config(runs_dir=tmp_path / "runs")
    plan = make_plan(brief, drop_feature=1)
    model = FakeModel(
        {
            "Script": make_script(brief, drop=1),
            "ScenePlan": [plan, plan, make_plan(brief)],
            "MusicChoice": {"mood": "tech", "bpm": 110, "reason": "x"},
            "Verdict": [VERDICT_PASS] * 3,
        }
    )
    svc = Service(config, {"strong": model, "fast": model}, StubTTS(), stub_renderer)
    run_dir = svc.run(brief).run_dir
    svc.approve(run_dir)
    assert svc.approve_scenes(run_dir).status == "stopped"  # the fixer couldn't tell key point 1
    spec = json.loads((run_dir / "spec.json").read_text())
    spec["scenes"][2]["covers"] = [1]  # the user tells it in scene 3 and approves again
    (run_dir / "spec.json").write_text(json.dumps(spec))
    assert svc.approve_scenes(run_dir).status == "done"
