import json
from contextlib import contextmanager
from types import SimpleNamespace

from reelhive.visuals.login import login


def test_manual_login_saves_state_privately_and_closes_browser(tmp_path, monkeypatch):
    visited, closed = [], []
    state = {"cookies": [], "origins": []}
    context = SimpleNamespace(new_page=lambda: SimpleNamespace(goto=visited.append), storage_state=lambda: state)
    browser = SimpleNamespace(new_context=lambda: context, close=lambda: closed.append(True))

    @contextmanager
    def playwright():
        yield SimpleNamespace(chromium=SimpleNamespace(launch=lambda **kwargs: browser))

    monkeypatch.setattr("reelhive.visuals.login.sync_playwright", playwright)
    output = tmp_path / "session.json"
    output.write_text("old")
    output.chmod(0o644)
    login("http://localhost:3000", output, confirm=lambda _: None)
    assert json.loads(output.read_text()) == state
    assert output.stat().st_mode & 0o777 == 0o600
    assert visited == ["http://localhost:3000"] and closed
