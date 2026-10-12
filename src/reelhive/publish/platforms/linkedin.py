"""LinkedIn: the Videos API (multipart upload with ETags, captions, finalize), then a post through the Posts API.

Post text is LinkedIn's "little text" format: reserved characters are escaped and hashtags become hashtag
templates, so the commentary appears exactly as written.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any
from urllib.parse import quote

import httpx
from pydantic import BaseModel

from reelhive.config import Publishing
from reelhive.publish import http as net
from reelhive.publish.accounts import Account
from reelhive.publish.http import PublishError, read, send
from reelhive.publish.platforms.base import Adapter, Posted, Progress, Upload, expiry
from reelhive.schemas.publish import HASHTAG, LinkedInCopy

TOKEN = "https://www.linkedin.com/oauth/v2/accessToken"
API = "https://api.linkedin.com"
RESERVED = re.compile(r"([\\|{}@\[\]()<>#*_~])")
PROCESSING_TIMEOUT = 600.0
POLL = 5.0


def little_text(text: str) -> str:
    """Commentary in LinkedIn's little text format: reserved characters escaped, #tags as hashtag templates."""
    out, position = [], 0
    for match in HASHTAG.finditer(text):
        out.append(RESERVED.sub(r"\\\1", text[position : match.start()]))
        out.append("{hashtag|\\#|" + match.group(1) + "}")
        position = match.end()
    out.append(RESERVED.sub(r"\\\1", text[position:]))
    return "".join(out)


class LinkedIn(Adapter):
    name = "linkedin"
    title = "LinkedIn"
    env = ("REELHIVE_LINKEDIN_CLIENT_ID", "REELHIVE_LINKEDIN_CLIENT_SECRET")
    authorize_endpoint = "https://www.linkedin.com/oauth/v2/authorization"
    scopes = ("openid", "profile", "w_member_social")
    pkce = False
    setup = "https://www.linkedin.com/developers/apps (products: Sign In with LinkedIn, Share on LinkedIn)"

    def scope_list(self, settings: Publishing) -> tuple[str, ...]:
        return (*self.scopes, "w_organization_social") if settings.linkedin.organization else self.scopes

    def exchange(self, http: httpx.Client, code: str, redirect_uri: str, verifier: str | None) -> dict[str, Any]:
        client_id, secret = self.credentials()
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": secret,
        }
        return send(http, "POST", TOKEN, data=data, what="LinkedIn sign-in").json()

    def identify(self, http: httpx.Client, token: dict[str, Any], settings: Publishing) -> Account:
        me = send(
            http,
            "GET",
            f"{API}/v2/userinfo",
            headers={"Authorization": f"Bearer {token['access_token']}"},
            what="LinkedIn profile lookup",
        ).json()
        return Account(
            platform=self.name,
            name=me.get("name") or me["sub"],
            id=f"urn:li:person:{me['sub']}",
            access_token=token["access_token"],
            refresh_token=token.get("refresh_token"),
            expires_at=expiry(token),
            refresh_expires_at=expiry(token, "refresh_token_expires_in"),
            scopes=str(token.get("scope", "")).replace(",", " ").split(),
        )

    def refresh(self, http: httpx.Client, account: Account) -> Account:
        if not account.refresh_token:  # LinkedIn issues refresh tokens to approved partner apps only
            raise PublishError("LinkedIn sign-in expired (tokens last 60 days): run `reelhive connect linkedin` again")
        client_id, secret = self.credentials()
        token = send(
            http,
            "POST",
            TOKEN,
            data={
                "grant_type": "refresh_token",
                "refresh_token": account.refresh_token,
                "client_id": client_id,
                "client_secret": secret,
            },
            what="LinkedIn token refresh",
        ).json()
        return account.model_copy(
            update={
                "access_token": token["access_token"],
                "expires_at": expiry(token),
                "refresh_token": token.get("refresh_token", account.refresh_token),
            }
        )

    def check(self, upload: Upload, settings: Publishing) -> tuple[list[str], list[str]]:
        failures = []
        if not 3 <= upload.duration <= 30 * 60:
            failures.append("LinkedIn takes videos of 3 seconds to 30 minutes")
        if not 75 * 1024 <= upload.size <= 500 * 1024 * 1024:
            failures.append("LinkedIn takes video files of 75 KB to 500 MB")
        return failures, []

    def post(
        self,
        http: httpx.Client,
        account: Account,
        upload: Upload,
        copy: BaseModel,
        settings: Publishing,
        progress: Progress,
    ) -> Posted:
        assert isinstance(copy, LinkedInCopy)
        headers = {
            "Authorization": f"Bearer {account.access_token}",
            "LinkedIn-Version": settings.linkedin.api_version,
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }
        owner = settings.linkedin.organization or account.id
        started = send(
            http,
            "POST",
            f"{API}/rest/videos",
            params={"action": "initializeUpload"},
            headers=headers,
            content=json.dumps(
                {
                    "initializeUploadRequest": {
                        "owner": owner,
                        "fileSizeBytes": upload.size,
                        "uploadCaptions": upload.subtitles is not None,
                        "uploadThumbnail": False,
                    }
                }
            ),
            what="LinkedIn upload start",
        ).json()["value"]
        video = started["video"]
        parts = []
        instructions = sorted(started["uploadInstructions"], key=lambda i: i["firstByte"])
        for n, part in enumerate(instructions, start=1):
            response = send(
                http,
                "PUT",
                part["uploadUrl"],
                headers={"Content-Type": "application/octet-stream"},
                content=read(upload.video, part["firstByte"], part["lastByte"]),
                what="LinkedIn upload",
            )
            parts.append(response.headers.get("etag", "").strip('"'))
            progress("Uploading to LinkedIn", n / len(instructions))
        notes = []
        if upload.subtitles and started.get("captionsUploadUrl"):
            try:
                self._captions(http, started["captionsUploadUrl"], upload)
            except PublishError as error:  # captions are optional for a feed video
                notes.append(f"Captions not added ({error})")
        send(
            http,
            "POST",
            f"{API}/rest/videos",
            params={"action": "finalizeUpload"},
            headers=headers,
            content=json.dumps(
                {
                    "finalizeUploadRequest": {
                        "video": video,
                        "uploadToken": started.get("uploadToken", ""),
                        "uploadedPartIds": parts,
                    }
                }
            ),
            what="LinkedIn upload finish",
        )
        progress("LinkedIn is processing the video", None)
        self._wait(http, headers, video)
        created = send(
            http,
            "POST",
            f"{API}/rest/posts",
            headers=headers,
            content=json.dumps(
                {
                    "author": owner,
                    "commentary": little_text(copy.commentary),
                    "visibility": settings.linkedin.visibility,
                    "distribution": {
                        "feedDistribution": "MAIN_FEED",
                        "targetEntities": [],
                        "thirdPartyDistributionChannels": [],
                    },
                    "content": {"media": {"title": copy.title, "id": video}},
                    "lifecycleState": "PUBLISHED",
                    "isReshareDisabledByAuthor": False,
                }
            ),
            what="LinkedIn post",
        )
        urn = created.headers.get("x-restli-id") or created.headers.get("x-linkedin-id") or video
        return Posted(id=urn, url=f"https://www.linkedin.com/feed/update/{urn}/", note="; ".join(notes) or None)

    def _captions(self, http: httpx.Client, url: str, upload: Upload) -> None:
        assert upload.subtitles
        metadata = {
            "format": "SRT",
            "formattedForEasyReader": True,
            "largeText": True,
            "source": "USER_PROVIDED",
            "locale": {"variant": "AMERICAN", "country": "US", "language": "EN"},
            "transcriptType": "CLOSED_CAPTION",
        }
        send(
            http,
            "POST",
            url,
            files={
                "metadata": (None, json.dumps(metadata)),
                "file": (upload.subtitles.name, upload.subtitles.read_bytes(), "text/plain"),
            },
            what="LinkedIn captions",
        )

    def _wait(self, http: httpx.Client, headers: dict[str, str], video: str) -> None:
        deadline = time.monotonic() + PROCESSING_TIMEOUT
        while True:
            state = send(
                http, "GET", f"{API}/rest/videos/{quote(video, safe='')}", headers=headers, what="LinkedIn video status"
            ).json()
            status = state.get("status")
            if status == "AVAILABLE":
                return
            if status == "PROCESSING_FAILED":
                raise PublishError(
                    f"LinkedIn could not process the video: {state.get('processingFailureReason', 'unknown')}"
                )
            if time.monotonic() > deadline:
                raise PublishError("LinkedIn is still processing the video; post it later from the run")
            net.sleep(POLL)
