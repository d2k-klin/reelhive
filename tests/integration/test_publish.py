"""Publishing end to end on a finished run: gates, drafted copy, approval, parallel posting, and a safe retry."""

import json

import httpx
import pytest
from conftest import VERDICT_PASS, FakeModel, StubTTS, make_plan, make_script, stub_renderer

from reelhive.core.service import Service
from reelhive.publish import accounts
from reelhive.publish import http as net
from reelhive.publish.accounts import Account
from reelhive.schemas.publish import LinkedInCopy, PostCopy

MUSIC = {"mood": "tech", "bpm": 110, "reason": "fits"}
COPY = {
    "youtube": {
        "title": "CostHive: find cloud waste in minutes",
        "description": "Scan every region.",
        "tags": ["finops"],
    },
    "linkedin": {"commentary": "Cloud bills grow silently. #FinOps", "title": "CostHive"},
}


@pytest.fixture(autouse=True)
def publishing_setup(tmp_path, monkeypatch):
    monkeypatch.setenv("REELHIVE_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(net, "sleep", lambda seconds: None)
    for name in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET"):
        monkeypatch.setenv(f"REELHIVE_{name}", "x")


class Platforms:
    """A mock of YouTube and LinkedIn; LinkedIn's post endpoint can be made to fail."""

    def __init__(self):
        self.linkedin_down = False
        self.uploads = {"youtube": 0, "linkedin": 0}

    def __call__(self, request):
        url = request.url
        if url.host == "www.googleapis.com" and request.method == "POST" and url.path.endswith("/videos"):
            self.uploads["youtube"] += 1
            return httpx.Response(200, headers={"location": "https://upload.example/s"})
        if url.host == "upload.example":
            return httpx.Response(201, json={"id": "yt1", "status": {"privacyStatus": "private"}})
        if url.path.endswith("/captions"):
            return httpx.Response(200, json={})
        if url.params.get("action") == "initializeUpload":
            self.uploads["linkedin"] += 1
            return httpx.Response(
                200,
                json={
                    "value": {
                        "video": "urn:li:video:1",
                        "uploadToken": "",
                        "uploadInstructions": [
                            {
                                "uploadUrl": "https://www.linkedin.com/dms-uploads/1",
                                "firstByte": 0,
                                "lastByte": int(json.loads(request.content)["initializeUploadRequest"]["fileSizeBytes"])
                                - 1,
                            }
                        ],
                    }
                },
            )
        if url.path.startswith("/dms-uploads/"):
            return httpx.Response(200, headers={"etag": "e1"})
        if url.params.get("action") == "finalizeUpload":
            return httpx.Response(200)
        if url.path.startswith("/rest/videos/"):
            return httpx.Response(200, json={"status": "AVAILABLE"})
        if url.path == "/rest/posts":
            if self.linkedin_down:
                return httpx.Response(422, json={"message": "commentary is invalid"})
            return httpx.Response(201, headers={"x-restli-id": "urn:li:share:5"})
        raise AssertionError(url)


def finished_run(config, brief, platforms_mock, copy=COPY):
    model = FakeModel(
        {
            "Script": make_script(brief),
            "ScenePlan": make_plan(brief),
            "MusicChoice": MUSIC,
            "Verdict": VERDICT_PASS,
            "PostCopy": copy,
        }
    )
    http = httpx.Client(transport=httpx.MockTransport(platforms_mock))
    service = Service(config, {"strong": model, "fast": model}, StubTTS(), stub_renderer, http=http)
    result = service.run(brief)
    assert result.status == "done"
    return service, result.run_dir, model


def sign_in(*platforms):
    for platform in platforms:
        ident = "urn:li:person:me" if platform == "linkedin" else "UC1"
        accounts.save(Account(platform=platform, name="me", id=ident, access_token="token"))


def test_drafting_is_blocked_before_any_model_call_when_a_platform_isnt_signed_in(config, brief):
    service, run_dir, model = finished_run(config, brief, Platforms())
    sign_in("youtube")
    job = service.draft_posts(run_dir, ["youtube", "linkedin"])
    assert job.status == "blocked" and any("LinkedIn: not signed in" in f for f in job.failures)
    assert "PostCopy" not in model.calls


def test_draft_edit_publish_in_parallel_then_retry_only_what_failed(config, brief):
    platforms = Platforms()
    platforms.linkedin_down = True
    service, run_dir, model = finished_run(config, brief, platforms)
    sign_in("youtube", "linkedin")
    events = []

    job = service.draft_posts(run_dir, ["linkedin", "youtube"], on_event=events.append)
    assert job.status == "awaiting_approval" and job.platforms == ["youtube", "linkedin"]
    assert job.posts.youtube.title.startswith("CostHive") and platforms.uploads == {"youtube": 0, "linkedin": 0}

    edited = job.posts.model_copy(
        update={"linkedin": LinkedInCopy(commentary="Edited by hand #FinOps", title="CostHive")}
    )
    service.save_posts(run_dir, edited)
    with pytest.raises(ValueError, match="one block per chosen platform"):
        service.save_posts(run_dir, PostCopy(youtube=edited.youtube))

    job = service.publish(run_dir, on_event=events.append)
    assert job.status == "partial"
    assert job.results["youtube"].status == "published" and job.results["youtube"].url == "https://youtu.be/yt1"
    assert job.results["linkedin"].status == "failed" and "commentary is invalid" in job.results["linkedin"].error
    started = [e.data["node"] for e in events if e.type == "node.started"]
    assert started[-3:][0] == "ready" and set(started[-2:]) == {"post_youtube", "post_linkedin"}

    platforms.linkedin_down = False
    job = service.publish(run_dir)
    assert job.status == "published" and job.results["linkedin"].url.endswith("urn:li:share:5/")
    assert platforms.uploads == {"youtube": 1, "linkedin": 2}  # YouTube was never uploaded twice
    saved = json.loads((run_dir / "publish/job.json").read_text())
    assert saved["status"] == "published" and "token" not in (run_dir / "publish/job.json").read_text()


def test_publishing_needs_an_approved_draft_and_a_finished_run(config, brief):
    service, run_dir, _ = finished_run(config, brief, Platforms())
    with pytest.raises(ValueError, match="draft"):
        service.publish(run_dir)


def test_an_interrupted_publish_is_never_silently_retried(config, brief):
    service, run_dir, _ = finished_run(config, brief, Platforms(), copy={"youtube": COPY["youtube"]})
    sign_in("youtube")
    service.draft_posts(run_dir, ["youtube"])
    data = json.loads((run_dir / "publish/job.json").read_text())
    data["status"] = "publishing"
    data["results"] = {"youtube": {"status": "publishing"}}
    (run_dir / "publish/job.json").write_text(json.dumps(data))
    job = service.publish_job(run_dir)
    assert job.status == "failed" and "check the platform" in job.results["youtube"].error
