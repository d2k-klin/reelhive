"""`reelhive run` with several briefs: all checked first, then made in turn, with a summary at the end."""

from pathlib import Path
from types import SimpleNamespace

import yaml
from typer.testing import CliRunner

from reelhive import cli
from tests.conftest import REPO_ROOT


def briefs(tmp_path: Path, *names: str) -> list[str]:
    base = yaml.safe_load((REPO_ROOT / "examples/briefs/low.yaml").read_text())
    paths = []
    for name in names:
        path = tmp_path / f"{name}.yaml"
        path.write_text(yaml.safe_dump(base | ({"duration": 5} if name == "broken" else {})))
        paths.append(str(path))
    return paths


def fake_service(monkeypatch, statuses: list[str]) -> list:
    made = []

    class Service:
        def __init__(self, config):
            pass

        def run(self, brief, on_event=None):
            status = statuses[len(made)]
            made.append(brief)
            if status == "error":
                raise RuntimeError("renderer crashed")
            return SimpleNamespace(status=status, video=Path("video.mp4"), run_dir=Path("runs/x"), report=["pace"])

    monkeypatch.setattr("reelhive.core.service.Service", Service)
    monkeypatch.setattr(cli, "load_config", lambda _: None)
    return made


def test_every_brief_is_checked_before_any_is_made(monkeypatch, tmp_path):
    made = fake_service(monkeypatch, ["done", "done"])
    result = CliRunner().invoke(cli.app, ["run", *briefs(tmp_path, "good", "broken")])
    assert result.exit_code == 2 and "broken.yaml" in result.output and not made


def test_a_batch_carries_on_past_a_failed_brief_and_reports_each(monkeypatch, tmp_path):
    made = fake_service(monkeypatch, ["done", "error", "stopped"])
    result = CliRunner().invoke(cli.app, ["run", *briefs(tmp_path, "bag", "tee", "mug")])
    assert len(made) == 3 and result.exit_code == 1
    summary = result.output.split("Batch")[1]
    assert "done" in summary and "failed" in summary and "renderer crashed" in summary and "stopped" in summary


def test_one_brief_still_reads_as_before(monkeypatch, tmp_path):
    fake_service(monkeypatch, ["done"])
    result = CliRunner().invoke(cli.app, ["run", *briefs(tmp_path, "bag")])
    assert result.exit_code == 0 and "Video ready" in result.output and "Batch" not in result.output
