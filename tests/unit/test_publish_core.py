"""Publishing building blocks: the copy limits, the job's state, saved accounts and the loopback sign-in."""

import socket
import stat
import threading
import urllib.error
import urllib.request
from urllib.parse import parse_qs, urlparse

import pytest
from pydantic import ValidationError

from reelhive.config import Publishing
from reelhive.publish import accounts, oauth
from reelhive.publish.accounts import Account
from reelhive.publish.http import PublishError
from reelhive.schemas.publish import (
    InstagramCopy,
    PostCopy,
    PostResult,
    PublishJob,
    TikTokCopy,
    YouTubeCopy,
    utf16_length,
)


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("REELHIVE_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("REELHIVE_YOUTUBE_CLIENT_ID", "id")
    monkeypatch.setenv("REELHIVE_YOUTUBE_CLIENT_SECRET", "secret")


def test_youtube_rejects_angle_brackets_and_oversized_tags():
    with pytest.raises(ValidationError, match="< and >"):
        YouTubeCopy(title="Fast <and> cheap", description="")
    with pytest.raises(ValidationError, match="30 characters"):
        YouTubeCopy(title="t", description="", tags=["#finops"])


def test_tiktok_counts_utf16_units_like_tiktok():
    assert utf16_length("🎬") == 2
    with pytest.raises(ValidationError, match="2200"):
        TikTokCopy(caption="🎬" * 1101)


def test_instagram_hashtag_limit():
    with pytest.raises(ValidationError, match="30 hashtags"):
        InstagramCopy(caption=" ".join(f"#t{i}" for i in range(31)))


def test_job_copy_must_match_its_platforms_and_settles_from_results():
    with pytest.raises(ValidationError, match="one block per chosen platform"):
        PublishJob(platforms=["youtube", "tiktok"], posts=PostCopy(tiktok=TikTokCopy(caption="c")))
    job = PublishJob(platforms=["tiktok", "youtube"])
    assert job.platforms == ["youtube", "tiktok"]  # canonical order
    job.results = {"youtube": PostResult(status="published"), "tiktok": PostResult(status="failed")}
    job.settle()
    assert job.status == "partial"
    job.results["tiktok"] = PostResult(status="published")
    job.settle()
    assert job.status == "published"


def test_accounts_are_saved_owner_only_and_shown_without_tokens(tmp_path):
    saved = accounts.save(Account(platform="youtube", name="CostHive", id="UC1", access_token="secret-token"))
    path = tmp_path / "home/accounts/youtube.json"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600 and stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    assert accounts.load("youtube") == saved and "secret-token" not in str(saved.public())
    assert accounts.remove("youtube") and accounts.load("youtube") is None


def test_an_account_close_to_expiry_is_refreshed():
    assert Account(platform="youtube", name="n", id="i", access_token="t", expires_at=1000).expiring(now=900)
    assert not Account(platform="youtube", name="n", id="i", access_token="t", expires_at=None).expiring()


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def redirect(port, query):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/callback?{query}", timeout=5).read()
    except urllib.error.HTTPError:
        pass


def test_consent_uses_pkce_s256_and_a_fresh_state():
    a, b = oauth.begin("youtube", Publishing()), oauth.begin("youtube", Publishing())
    query = parse_qs(urlparse(a.url).query)
    assert a.state != b.state and query["code_challenge_method"] == ["S256"] and a.verifier
    assert query["access_type"] == ["offline"] and a.redirect_uri == "http://localhost:8765/callback"


def test_the_loopback_listener_takes_the_code_only_with_its_own_state():
    consent = oauth.begin("youtube", Publishing())
    port = free_port()
    ready = threading.Event()
    threading.Thread(
        target=lambda: ready.wait(5) and redirect(port, f"state={consent.state}&code=abc"), daemon=True
    ).start()
    assert oauth.wait_for_code(consent, port, timeout=10, ready=ready) == "abc"

    ready = threading.Event()
    threading.Thread(target=lambda: ready.wait(5) and redirect(port, "state=forged&code=abc"), daemon=True).start()
    with pytest.raises(PublishError, match="did not match"):
        oauth.wait_for_code(consent, port, timeout=10, ready=ready)


def test_a_denied_consent_is_reported():
    consent = oauth.begin("youtube", Publishing())
    port = free_port()
    ready = threading.Event()
    query = f"state={consent.state}&error=access_denied&error_description=The+user+said+no"
    threading.Thread(target=lambda: ready.wait(5) and redirect(port, query), daemon=True).start()
    with pytest.raises(PublishError, match="The user said no"):
        oauth.wait_for_code(consent, port, timeout=10, ready=ready)
