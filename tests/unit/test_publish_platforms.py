"""Each platform adapter against a mock of the platform's API: the requests it sends, in order, and what it returns."""

import json
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from reelhive.config import Publishing
from reelhive.publish import http as net
from reelhive.publish.accounts import Account
from reelhive.publish.http import PublishError, send
from reelhive.publish.platforms import ADAPTERS, linkedin, tiktok, youtube
from reelhive.publish.platforms.base import Upload
from reelhive.schemas.publish import InstagramCopy, LinkedInCopy, TikTokCopy, YouTubeCopy


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    monkeypatch.setattr(net, "sleep", lambda seconds: None)
    for name, value in {
        "REELHIVE_YOUTUBE_CLIENT_ID": "yt-id",
        "REELHIVE_YOUTUBE_CLIENT_SECRET": "yt-secret",
        "REELHIVE_LINKEDIN_CLIENT_ID": "li-id",
        "REELHIVE_LINKEDIN_CLIENT_SECRET": "li-secret",
        "REELHIVE_TIKTOK_CLIENT_KEY": "tt-key",
        "REELHIVE_TIKTOK_CLIENT_SECRET": "tt-secret",
        "REELHIVE_META_APP_ID": "meta-id",
        "REELHIVE_META_APP_SECRET": "meta-secret",
    }.items():
        monkeypatch.setenv(name, value)


@pytest.fixture
def upload(tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(bytes(range(256)) * 100)  # 25,600 bytes
    srt = tmp_path / "video.srt"
    srt.write_text("1\n00:00:00,300 --> 00:00:01,300\nHello\n")
    return Upload(video=video, subtitles=srt, size=25_600, duration=30.0, width=1080, height=1920)


def account(platform, **extra):
    return Account(
        platform=platform,
        name="me",
        id="urn:li:person:abc" if platform == "linkedin" else "acct-1",
        access_token="secret-token",
        extra=extra,
    )


def client(handler):
    calls = []

    def record(request):
        calls.append(request)
        return handler(request)

    return httpx.Client(transport=httpx.MockTransport(record)), calls


def no_progress(task, share):
    pass


def test_send_retries_server_errors_and_reports_the_platforms_reason():
    replies = iter([httpx.Response(503), httpx.Response(200, json={"ok": True})])
    http, calls = client(lambda r: next(replies))
    assert send(http, "GET", "https://api.example/x").json() == {"ok": True} and len(calls) == 2
    http, _ = client(lambda r: httpx.Response(400, json={"error": {"message": "title too long"}}))
    with pytest.raises(PublishError, match=r"upload failed \(400\): title too long"):
        send(http, "POST", "https://api.example/x", what="upload", headers={"Authorization": "Bearer secret-token"})


def test_youtube_resumes_from_the_range_youtube_reports_and_adds_captions(upload, monkeypatch):
    monkeypatch.setattr(youtube, "CHUNK", 10_000)

    def handler(request):
        if request.url.path == "/upload/youtube/v3/videos" and request.method == "POST":
            body = json.loads(request.content)
            assert body["status"] == {
                "privacyStatus": "private",
                "selfDeclaredMadeForKids": False,
                "containsSyntheticMedia": True,
            }
            assert request.headers["x-upload-content-length"] == "25600"
            return httpx.Response(200, headers={"location": "https://upload.example/session"})
        if request.url.host == "upload.example":
            first = int(request.headers["content-range"].split()[1].split("-")[0])
            if first == 0:  # YouTube kept only part of the first chunk
                return httpx.Response(308, headers={"range": "bytes=0-4999"})
            if not request.headers["content-range"].endswith("25599/25600"):
                last = request.headers["content-range"].split("-")[1].split("/")[0]
                return httpx.Response(308, headers={"range": f"bytes=0-{last}"})
            return httpx.Response(200, json={"id": "vid123", "status": {"privacyStatus": "private"}})
        if request.url.path == "/upload/youtube/v3/captions":
            assert b'"videoId": "vid123"' in request.content and b"00:00:00,300 --> 00:00:01,300" in request.content
            return httpx.Response(200, json={"id": "cap1"})
        raise AssertionError(request.url)

    http, calls = client(handler)
    copy = YouTubeCopy(title="CostHive in 60 seconds", description="Find cloud waste.", tags=["finops"])
    posted = ADAPTERS["youtube"].post(http, account("youtube"), upload, copy, Publishing(), no_progress)
    assert posted.id == "vid123" and posted.url == "https://youtu.be/vid123" and posted.note is None
    ranges = [c.headers["content-range"] for c in calls if c.url.host == "upload.example"]
    assert ranges == [
        "bytes 0-9999/25600",
        "bytes 5000-14999/25600",
        "bytes 15000-24999/25600",
        "bytes 25000-25599/25600",
    ]


def test_youtube_caption_failure_keeps_the_published_video(upload):
    def handler(request):
        if request.url.path.endswith("/captions"):
            return httpx.Response(403, json={"error": {"message": "forbidden"}})
        if request.method == "POST":
            return httpx.Response(200, headers={"location": "https://upload.example/s"})
        return httpx.Response(201, json={"id": "v1", "status": {"privacyStatus": "public"}})

    http, _ = client(handler)
    settings = Publishing(youtube={"privacy": "public"})
    posted = ADAPTERS["youtube"].post(
        http, account("youtube"), upload, YouTubeCopy(title="t", description="d"), settings, no_progress
    )
    assert posted.id == "v1" and "Captions not added" in posted.note


def test_linkedin_little_text_escapes_reserved_characters_and_templates_hashtags():
    assert linkedin.little_text("Save 40% (today) on cloud_bills #FinOps #cloud") == (
        "Save 40% \\(today\\) on cloud\\_bills {hashtag|\\#|FinOps} {hashtag|\\#|cloud}"
    )


def test_linkedin_uploads_parts_in_order_finalizes_with_their_etags_and_posts(upload):
    statuses = iter(["PROCESSING", "AVAILABLE"])

    def handler(request):
        url = request.url
        if url.path == "/rest/videos" and url.params.get("action") == "initializeUpload":
            body = json.loads(request.content)["initializeUploadRequest"]
            assert body == {
                "owner": "urn:li:person:abc",
                "fileSizeBytes": 25600,
                "uploadCaptions": True,
                "uploadThumbnail": False,
            }
            assert request.headers["linkedin-version"] == "202609"
            return httpx.Response(
                200,
                json={
                    "value": {
                        "video": "urn:li:video:V1",
                        "uploadToken": "tok",
                        "captionsUploadUrl": "https://www.linkedin.com/dms-mpf-uploads/captions",
                        "uploadInstructions": [
                            {
                                "uploadUrl": "https://www.linkedin.com/dms-uploads/p2",
                                "firstByte": 12800,
                                "lastByte": 25599,
                            },
                            {"uploadUrl": "https://www.linkedin.com/dms-uploads/p1", "firstByte": 0, "lastByte": 12799},
                        ],
                    }
                },
            )
        if url.path.startswith("/dms-uploads/"):
            assert len(request.content) == 12800
            return httpx.Response(200, headers={"etag": f'"{url.path[-2:]}-etag"'})
        if url.path == "/dms-mpf-uploads/captions":
            assert b'"format": "SRT"' in request.content and b"Hello" in request.content
            return httpx.Response(201)
        if url.params.get("action") == "finalizeUpload":
            assert json.loads(request.content)["finalizeUploadRequest"]["uploadedPartIds"] == ["p1-etag", "p2-etag"]
            return httpx.Response(200)
        if url.path.startswith("/rest/videos/"):
            return httpx.Response(200, json={"status": next(statuses)})
        if url.path == "/rest/posts":
            body = json.loads(request.content)
            assert body["content"]["media"] == {"title": "CostHive", "id": "urn:li:video:V1"}
            assert body["commentary"] == "Cloud bills grow {hashtag|\\#|finops}" and body["visibility"] == "PUBLIC"
            return httpx.Response(201, headers={"x-restli-id": "urn:li:share:9"})
        raise AssertionError(url)

    http, _ = client(handler)
    copy = LinkedInCopy(commentary="Cloud bills grow #finops", title="CostHive")
    posted = ADAPTERS["linkedin"].post(http, account("linkedin"), upload, copy, Publishing(), no_progress)
    assert posted.id == "urn:li:share:9" and posted.url == "https://www.linkedin.com/feed/update/urn:li:share:9/"


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        (1_000, (1_000, 1)),
        (10 * 2**20, (10 * 2**20, 1)),
        (25 * 2**20 + 7, (10 * 2**20, 2)),
        (30 * 2**20, (10 * 2**20, 3)),
    ],
)
def test_tiktok_chunks_merge_the_remainder_into_the_last_one(size, expected):
    assert tiktok.chunking(size) == expected


def tiktok_handler(privacy_options, mode_seen, chunks):
    def handler(request):
        path = request.url.path
        if path.endswith("/creator_info/query/"):
            return httpx.Response(
                200,
                json={
                    "data": {"privacy_level_options": privacy_options, "max_video_post_duration_sec": 600},
                    "error": {"code": "ok"},
                },
            )
        if path.endswith("/video/init/"):
            mode_seen.append(path)
            return httpx.Response(
                200,
                json={
                    "data": {"publish_id": "p1", "upload_url": "https://upload.tiktok.example/u"},
                    "error": {"code": "ok"},
                },
            )
        if request.url.host == "upload.tiktok.example":
            chunks.append(request.headers["content-range"])
            return httpx.Response(201)
        if path.endswith("/status/fetch/"):
            status = "PUBLISH_COMPLETE" if "/publish/video/init/" in mode_seen[0] else "SEND_TO_USER_INBOX"
            return httpx.Response(
                200, json={"data": {"status": status, "publicaly_available_post_id": [777]}, "error": {"code": "ok"}}
            )
        raise AssertionError(path)

    return handler


def test_tiktok_direct_post_respects_the_creators_privacy_and_links_the_video(upload):
    seen, chunks = [], []
    http, calls = client(tiktok_handler(["PUBLIC_TO_EVERYONE", "SELF_ONLY"], seen, chunks))
    settings = Publishing(tiktok={"mode": "direct", "privacy": "SELF_ONLY"})
    posted = ADAPTERS["tiktok"].post(
        http,
        account("tiktok", username="costhive"),
        upload,
        TikTokCopy(caption="Find waste #finops"),
        settings,
        no_progress,
    )
    init = json.loads(next(c for c in calls if c.url.path.endswith("/video/init/")).content)
    assert init["post_info"]["privacy_level"] == "SELF_ONLY" and init["post_info"]["is_aigc"] is True
    assert init["source_info"] == {
        "source": "FILE_UPLOAD",
        "video_size": 25600,
        "chunk_size": 25600,
        "total_chunk_count": 1,
    }
    assert chunks == ["bytes 0-25599/25600"]
    assert posted.url == "https://www.tiktok.com/@costhive/video/777"


def test_tiktok_draft_goes_to_the_inbox_without_a_caption(upload):
    seen, chunks = [], []
    http, calls = client(tiktok_handler([], seen, chunks))
    posted = ADAPTERS["tiktok"].post(
        http, account("tiktok"), upload, TikTokCopy(caption="c"), Publishing(), no_progress
    )
    assert seen == ["/v2/post/publish/inbox/video/init/"] and "post_info" not in json.loads(calls[0].content)
    assert posted.url is None and "inbox" in posted.note


def test_tiktok_refuses_a_privacy_the_account_cant_use(upload):
    http, _ = client(tiktok_handler(["SELF_ONLY"], [], []))
    settings = Publishing(tiktok={"mode": "direct", "privacy": "PUBLIC_TO_EVERYONE"})
    with pytest.raises(PublishError, match="not PUBLIC_TO_EVERYONE"):
        ADAPTERS["tiktok"].post(http, account("tiktok"), upload, TikTokCopy(caption="c"), settings, no_progress)


def test_instagram_resumable_reel_waits_for_processing_then_publishes(upload):
    statuses = iter(["IN_PROGRESS", "FINISHED"])

    def handler(request):
        url = request.url
        if url.path == "/v23.0/acct-1/media":
            form = parse_qs(request.content.decode())
            assert form["media_type"] == ["REELS"] and form["upload_type"] == ["resumable"]
            return httpx.Response(200, json={"id": "c1", "uri": "https://rupload.facebook.com/ig-api-upload/v23.0/c1"})
        if url.host == "rupload.facebook.com":
            assert request.headers["authorization"] == "OAuth secret-token"
            assert request.headers["offset"] == "0" and request.headers["file_size"] == "25600"
            return httpx.Response(200, json={"success": True})
        if url.path == "/v23.0/c1":
            return httpx.Response(200, json={"status_code": next(statuses)})
        if url.path == "/v23.0/acct-1/media_publish":
            assert parse_qs(request.content.decode())["creation_id"] == ["c1"]
            return httpx.Response(200, json={"id": "m1"})
        if url.path == "/v23.0/m1":
            return httpx.Response(200, json={"permalink": "https://www.instagram.com/reel/abc/"})
        raise AssertionError(url)

    http, _ = client(handler)
    posted = ADAPTERS["instagram"].post(
        http, account("instagram"), upload, InstagramCopy(caption="Hi #finops"), Publishing(), no_progress
    )
    assert posted.id == "m1" and posted.url == "https://www.instagram.com/reel/abc/"


def test_instagram_processing_error_is_reported(upload):
    def handler(request):
        if request.url.path.endswith("/media"):
            return httpx.Response(200, json={"id": "c1", "uri": "https://rupload.facebook.com/x"})
        if request.url.host == "rupload.facebook.com":
            return httpx.Response(200)
        return httpx.Response(200, json={"status_code": "ERROR", "status": "Error: video too short"})

    http, _ = client(handler)
    with pytest.raises(PublishError, match="video too short"):
        ADAPTERS["instagram"].post(
            http, account("instagram"), upload, InstagramCopy(caption="c"), Publishing(), no_progress
        )


@pytest.mark.parametrize("platform", ["youtube", "linkedin", "tiktok", "instagram"])
def test_consent_urls_carry_state_scopes_and_pkce_where_supported(platform):
    adapter = ADAPTERS[platform]
    url = adapter.authorize_url("http://localhost:8765/callback", "st4te", "ch4llenge", Publishing())
    query = parse_qs(urlparse(url).query)
    assert query["state"] == ["st4te"] and query["redirect_uri"] == ["http://localhost:8765/callback"]
    assert query[adapter.client_id_param][0].endswith(("id", "key"))
    assert ("code_challenge" in query) == adapter.pkce


def test_portrait_platforms_warn_about_landscape_video_and_linkedin_checks_size(upload):
    landscape = Upload(upload.video, None, upload.size, 30.0, 1920, 1080)
    assert (
        ADAPTERS["tiktok"].check(landscape, Publishing())[1] and ADAPTERS["instagram"].check(landscape, Publishing())[1]
    )
    tiny = Upload(upload.video, None, 1_000, 2.0, 1080, 1920)
    failures, _ = ADAPTERS["linkedin"].check(tiny, Publishing())
    assert len(failures) == 2


def test_missing_developer_app_says_what_to_set(monkeypatch):
    monkeypatch.delenv("REELHIVE_TIKTOK_CLIENT_KEY")
    with pytest.raises(PublishError, match="REELHIVE_TIKTOK_CLIENT_KEY"):
        ADAPTERS["tiktok"].credentials()


SIGN_IN = {
    "youtube": {
        "/token": {"access_token": "a", "refresh_token": "r", "expires_in": 3599, "scope": "s1 s2"},
        "/youtube/v3/channels": {"items": [{"id": "UC1", "snippet": {"title": "CostHive"}}]},
    },
    "linkedin": {
        "/oauth/v2/accessToken": {"access_token": "a", "expires_in": 5184000, "scope": "openid,w_member_social"},
        "/v2/userinfo": {"sub": "abc", "name": "Dav K"},
    },
    "tiktok": {
        "/v2/oauth/token/": {
            "access_token": "a",
            "open_id": "oid",
            "refresh_token": "r",
            "expires_in": 86400,
            "refresh_expires_in": 31536000,
            "scope": "video.publish,video.upload",
        },
        "/v2/user/info/": {"data": {"user": {"open_id": "oid", "username": "costhive"}}, "error": {"code": "ok"}},
    },
    "instagram": {
        "/v23.0/oauth/access_token": {"access_token": "a", "expires_in": 5183944},
        "/v23.0/me/accounts": {
            "data": [
                {"name": "No IG page"},
                {"name": "CostHive", "instagram_business_account": {"id": "1784", "username": "costhive"}},
            ]
        },
    },
}
EXPECTED = {
    "youtube": ("CostHive", "UC1"),
    "linkedin": ("Dav K", "urn:li:person:abc"),
    "tiktok": ("@costhive", "oid"),
    "instagram": ("@costhive", "1784"),
}


@pytest.mark.parametrize("platform", list(SIGN_IN))
def test_sign_in_exchanges_the_code_and_saves_who_posts(platform, tmp_path, monkeypatch):
    from reelhive.publish import accounts, oauth

    monkeypatch.setenv("REELHIVE_HOME", str(tmp_path))
    routes = SIGN_IN[platform]

    def handler(request):
        if request.url.path in routes:
            if request.method == "POST" and "token" in request.url.path.lower():
                form = parse_qs(request.content.decode())
                assert form["code"] == ["the-code"] and ("code_verifier" in form) == ADAPTERS[platform].pkce
            return httpx.Response(200, json=routes[request.url.path])
        raise AssertionError(request.url)

    http, _ = client(handler)
    consent = oauth.begin(platform, Publishing())
    saved = oauth.finish(consent, "the-code", Publishing(), http)
    assert (saved.name, saved.id) == EXPECTED[platform] and accounts.load(platform) == saved
    assert saved.expires_at and saved.access_token == "a"


@pytest.mark.parametrize("platform", ["youtube", "linkedin", "tiktok"])
def test_refresh_uses_the_refresh_token_or_asks_to_sign_in_again(platform):
    token = {"access_token": "fresh", "expires_in": 3600, "refresh_token": "r2", "open_id": "oid"}
    http, calls = client(lambda r: httpx.Response(200, json=token))
    stale = account(platform).model_copy(update={"refresh_token": "r1", "expires_at": 1.0})
    fresh = ADAPTERS[platform].ready(http, stale)
    assert fresh.access_token == "fresh" and fresh.expires_at > 1000 and "refresh_token" in calls[0].content.decode()
    with pytest.raises(PublishError, match=f"reelhive connect {platform}"):
        ADAPTERS[platform].refresh(http, account(platform))


def test_instagram_refreshes_a_valid_long_lived_token_and_rejects_an_expired_one():
    http, calls = client(lambda r: httpx.Response(200, json={"access_token": "fresh", "expires_in": 5184000}))
    soon = account("instagram").model_copy(update={"expires_at": __import__("time").time() + 60})
    assert ADAPTERS["instagram"].ready(http, soon).access_token == "fresh"
    assert calls[0].url.params["grant_type"] == "fb_exchange_token"
    with pytest.raises(PublishError, match="reelhive connect instagram"):
        ADAPTERS["instagram"].refresh(http, account("instagram").model_copy(update={"expires_at": 1.0}))


def test_instagram_needs_a_linked_business_account():
    from reelhive.publish.platforms.instagram import Instagram

    http, _ = client(lambda r: httpx.Response(200, json={"data": [{"name": "Page without IG"}]}))
    with pytest.raises(PublishError, match="Business or Creator"):
        Instagram().identify(http, {"access_token": "a", "expires_in": 1}, Publishing())
