"""TikTok: the Content Posting API with a direct file upload.

`draft` (the default) sends the video to the creator's TikTok inbox to caption and post in the app; the inbox API
takes no caption, so the drafted caption is kept with the result to paste in. `direct` posts straight away, with
the caption and the privacy the creator's account allows. TikTok keeps posts from apps it hasn't audited private.
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx
from pydantic import BaseModel

from reelhive.config import Publishing
from reelhive.publish import http as net
from reelhive.publish.accounts import Account
from reelhive.publish.http import PublishError, read, send
from reelhive.publish.platforms.base import Adapter, Posted, Progress, Upload, expiry
from reelhive.schemas.publish import TikTokCopy

API = "https://open.tiktokapis.com/v2"
MIN_CHUNK = 5 * 1024 * 1024
CHUNK = 10 * 1024 * 1024  # 5-64 MB per chunk; the last one absorbs the remainder (TikTok's rule)
MAX_BYTES = 4 * 1024**3
PROCESSING_TIMEOUT = 600.0
POLL = 5.0


def chunking(size: int) -> tuple[int, int]:
    """(chunk_size, total_chunk_count) as TikTok counts them: whole chunks, the remainder joining the last."""
    if size < MIN_CHUNK:
        return size, 1
    return CHUNK, max(1, size // CHUNK)


def _data(response: httpx.Response, what: str) -> dict[str, Any]:
    body = response.json()
    error = body.get("error") or {}
    if error.get("code", "ok") != "ok":
        raise PublishError(f"{what} failed: {error.get('message') or error.get('code')}")
    return body.get("data") or {}


class TikTok(Adapter):
    name = "tiktok"
    title = "TikTok"
    env = ("REELHIVE_TIKTOK_CLIENT_KEY", "REELHIVE_TIKTOK_CLIENT_SECRET")
    authorize_endpoint = "https://www.tiktok.com/v2/auth/authorize/"
    client_id_param = "client_key"
    scopes = ("user.info.basic", "user.info.profile", "video.upload", "video.publish")
    scope_separator = ","
    setup = "https://developers.tiktok.com/apps (products: Login Kit, Content Posting API)"

    def _token(self, http: httpx.Client, data: dict[str, str], what: str) -> dict[str, Any]:
        client_key, secret = self.credentials()
        token = send(
            http,
            "POST",
            f"{API}/oauth/token/",
            data={"client_key": client_key, "client_secret": secret, **data},
            what=what,
        ).json()
        if "access_token" not in token:
            raise PublishError(f"{what} failed: {token.get('error_description') or token.get('error') or token}")
        return token

    def exchange(self, http: httpx.Client, code: str, redirect_uri: str, verifier: str | None) -> dict[str, Any]:
        data = {"code": code, "grant_type": "authorization_code", "redirect_uri": redirect_uri}
        if verifier:
            data["code_verifier"] = verifier
        return self._token(http, data, "TikTok sign-in")

    def identify(self, http: httpx.Client, token: dict[str, Any], settings: Publishing) -> Account:
        user = _data(
            send(
                http,
                "GET",
                f"{API}/user/info/",
                params={"fields": "open_id,username,display_name"},
                headers={"Authorization": f"Bearer {token['access_token']}"},
                what="TikTok profile lookup",
            ),
            "TikTok profile lookup",
        ).get("user", {})
        return Account(
            platform=self.name,
            name=f"@{user['username']}" if user.get("username") else user.get("display_name") or token["open_id"],
            id=token["open_id"],
            access_token=token["access_token"],
            refresh_token=token.get("refresh_token"),
            expires_at=expiry(token),
            refresh_expires_at=expiry(token, "refresh_expires_in"),
            scopes=str(token.get("scope", "")).split(","),
            extra={"username": user.get("username", "")},
        )

    def refresh(self, http: httpx.Client, account: Account) -> Account:
        if not account.refresh_token:
            raise PublishError("TikTok sign-in expired: run `reelhive connect tiktok` again")
        token = self._token(
            http, {"grant_type": "refresh_token", "refresh_token": account.refresh_token}, "TikTok token refresh"
        )
        return account.model_copy(
            update={
                "access_token": token["access_token"],
                "expires_at": expiry(token),
                "refresh_token": token.get("refresh_token", account.refresh_token),
                "refresh_expires_at": expiry(token, "refresh_expires_in") or account.refresh_expires_at,
            }
        )

    def check(self, upload: Upload, settings: Publishing) -> tuple[list[str], list[str]]:
        failures, warnings = [], []
        if upload.duration < 3:
            failures.append("TikTok takes videos of at least 3 seconds")
        if upload.size > MAX_BYTES:
            failures.append("TikTok takes video files up to 4 GB")
        if not upload.portrait:
            warnings.append("TikTok is vertical: a 16:9 or 1:1 video shows with bars; make a 9:16 cut for it")
        return failures, warnings

    def post(
        self,
        http: httpx.Client,
        account: Account,
        upload: Upload,
        copy: BaseModel,
        settings: Publishing,
        progress: Progress,
    ) -> Posted:
        assert isinstance(copy, TikTokCopy)
        options = settings.tiktok
        headers = {"Authorization": f"Bearer {account.access_token}", "Content-Type": "application/json; charset=UTF-8"}
        chunk, count = chunking(upload.size)
        source = {"source": "FILE_UPLOAD", "video_size": upload.size, "chunk_size": chunk, "total_chunk_count": count}
        if options.mode == "direct":
            creator = _data(
                send(
                    http, "POST", f"{API}/post/publish/creator_info/query/", headers=headers, what="TikTok creator info"
                ),
                "TikTok creator info",
            )
            if options.privacy not in creator.get("privacy_level_options", []):
                raise PublishError(
                    f"this TikTok account can post as {', '.join(creator.get('privacy_level_options', []))}, "
                    f"not {options.privacy}: change publishing.tiktok.privacy"
                )
            longest = creator.get("max_video_post_duration_sec")
            if longest and upload.duration > longest:
                raise PublishError(f"this TikTok account posts videos up to {longest} seconds")
            body: dict[str, Any] = {
                "post_info": {
                    "title": copy.caption,
                    "privacy_level": options.privacy,
                    "disable_comment": not options.allow_comments or bool(creator.get("comment_disabled")),
                    "disable_duet": not options.allow_duet or bool(creator.get("duet_disabled")),
                    "disable_stitch": not options.allow_stitch or bool(creator.get("stitch_disabled")),
                    "is_aigc": settings.label_ai,
                },
                "source_info": source,
            }
            endpoint = f"{API}/post/publish/video/init/"
        else:
            body, endpoint = {"source_info": source}, f"{API}/post/publish/inbox/video/init/"
        started = _data(
            send(http, "POST", endpoint, headers=headers, content=json.dumps(body), what="TikTok upload start"),
            "TikTok upload start",
        )
        for n in range(count):
            first = n * chunk
            last = upload.size - 1 if n == count - 1 else first + chunk - 1
            send(
                http,
                "PUT",
                started["upload_url"],
                headers={"Content-Type": "video/mp4", "Content-Range": f"bytes {first}-{last}/{upload.size}"},
                content=read(upload.video, first, last),
                what="TikTok upload",
            )
            progress("Uploading to TikTok", (n + 1) / count)
        progress("TikTok is processing the video", None)
        state = self._wait(http, headers, started["publish_id"], options.mode)
        if options.mode == "draft":
            return Posted(
                id=started["publish_id"],
                url=None,
                note="Sent to your TikTok inbox: open TikTok to finish the post and paste the drafted caption",
            )
        posted = state.get("publicaly_available_post_id") or []  # TikTok's own spelling
        username = account.extra.get("username")
        url = f"https://www.tiktok.com/@{username}/video/{posted[0]}" if posted and username else None
        note = None if posted else "Posted; it appears once TikTok's review finishes (private posts never get a link)"
        return Posted(id=str(posted[0]) if posted else started["publish_id"], url=url, note=note)

    def _wait(self, http: httpx.Client, headers: dict[str, str], publish_id: str, mode: str) -> dict[str, Any]:
        done = "SEND_TO_USER_INBOX" if mode == "draft" else "PUBLISH_COMPLETE"
        deadline = time.monotonic() + PROCESSING_TIMEOUT
        while True:
            state = _data(
                send(
                    http,
                    "POST",
                    f"{API}/post/publish/status/fetch/",
                    headers=headers,
                    content=json.dumps({"publish_id": publish_id}),
                    what="TikTok post status",
                ),
                "TikTok post status",
            )
            status = state.get("status")
            if status in (done, "PUBLISH_COMPLETE"):
                return state
            if status == "FAILED":
                raise PublishError(f"TikTok could not post the video: {state.get('fail_reason', 'unknown')}")
            if time.monotonic() > deadline:
                raise PublishError("TikTok is still processing the video; check the TikTok app")
            net.sleep(POLL)
