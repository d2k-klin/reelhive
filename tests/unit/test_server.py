from fastapi.testclient import TestClient

from reelhive.config import Config
from reelhive.core.events import EventBus
from reelhive.core.workspace import Workspace
from reelhive.schemas.brief import Brief
from reelhive.server.app import create_app
from reelhive.server.security import validate_host


def sample_brief() -> Brief:
    return Brief(
        audience="Local developers",
        storyline="Show a secure local workflow",
        features=["Script approval"],
        closing="Make the cut",
        visuals={"source": "none"},
    )


def test_local_api_rejects_missing_token_host_and_origin(tmp_path):
    workspace = Workspace(Config(runs_dir=tmp_path / "runs"))
    with TestClient(create_app(workspace=workspace, token="secret"), base_url="http://127.0.0.1") as client:
        assert client.get("/api/health").status_code == 401
        assert client.get("/api/health?token=secret", headers={"host": "evil.example"}).status_code == 403
        response = client.post(
            "/api/briefs/validate?token=secret",
            headers={"origin": "https://evil.example"},
            json=sample_brief().model_dump(mode="json"),
        )
        assert response.status_code == 403
        response = client.post(
            "/api/briefs/validate?token=secret",
            headers={"origin": "http://testserver"},
            json=sample_brief().model_dump(mode="json"),
        )
        assert response.status_code == 403


def test_run_files_and_sse_replay_stay_inside_workspace(tmp_path):
    workspace = Workspace(Config(runs_dir=tmp_path / "runs"))
    run = workspace.create(sample_brief(), start=False)
    path = workspace.path(run.id)
    EventBus(path / "run.log.jsonl").emit("node.started", node="script")
    EventBus(path / "run.log.jsonl").emit("node.finished", node="script", status="completed")
    headers = {"host": "127.0.0.1", "origin": "http://127.0.0.1"}
    with TestClient(create_app(workspace=workspace, token="secret"), base_url="http://127.0.0.1") as client:
        replay = client.get(f"/api/runs/{run.id}/events?token=secret&after=1&follow=false", headers=headers)
        assert replay.status_code == 200 and '"id": 2' in replay.text and '"id": 1' not in replay.text
        assert client.get(f"/api/runs/{run.id}/files/../config.json?token=secret", headers=headers).status_code == 404
        secret_setting = client.put(
            "/api/settings?token=secret",
            headers=headers,
            json={**Config().model_dump(mode="json"), "api_key": "must-not-be-accepted"},
        )
        assert secret_setting.status_code == 422


def test_loopback_bind_validation():
    validate_host("127.0.0.1")
    try:
        validate_host("0.0.0.0")
    except ValueError as error:
        assert "127.0.0.1" in str(error)
    else:
        raise AssertionError("non-loopback bind was accepted")
