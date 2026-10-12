"""YouTube: Data API v3 resumable upload, then the subtitles as an English caption track.

Uploads from an API project that Google hasn't audited are locked to private viewing, whatever the requested
privacy, so the default privacy is private and the result says so when YouTube keeps it private.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import httpx
from pydantic import BaseModel

from reelhive.config import Publishing
from reelhive.publish.accounts import Account
from reelhive.publish.http import PublishError, read, send
from reelhive.publish.platforms.base import Adapter, Posted, Progress, Upload, expiry
from reelhive.schemas.publish import YouTubeCopy

TOKEN = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/youtube/v3"
UPLOAD = "https://www.googleapis.com/upload/youtube/v3"
CHUNK = 32 * 256 * 1024  # 8 MiB: a multiple of 256 KiB, as resumable chunks must be


class YouTube(Adapter):
    name = "youtube"
    title = "YouTube"
    env = ("REELHIVE_YOUTUBE_CLIENT_ID", "REELHIVE_YOUTUBE_CLIENT_SECRET")
    authorize_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
    # upload for the video; force-ssl for the caption track
    scopes = ("https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.force-ssl")
    setup = "https://console.cloud.google.com/apis/credentials (OAuth client, type Desktop app)"

    def authorize_params(self, settings: Publishing) -> dict[str, str]:
        return {"access_type": "offline", "prompt": "consent"}  # a refresh token every time

    def exchange(self, http: httpx.Client, code: str, redirect_uri: str, verifier: str | None) -> dict[str, Any]:
        client_id, secret = self.credentials()
        data = {
            "code": code,
            "client_id": client_id,
            "client_secret": secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        if verifier:
            data["code_verifier"] = verifier
        return send(http, "POST", TOKEN, data=data, what="YouTube sign-in").json()

    def identify(self, http: httpx.Client, token: dict[str, Any], settings: Publishing) -> Account:
        headers = {"Authorization": f"Bearer {token['access_token']}"}
        channels = send(
            http,
            "GET",
            f"{API}/channels",
            params={"part": "snippet", "mine": "true"},
            headers=headers,
            what="YouTube channel lookup",
        ).json()
        items = channels.get("items") or []
        if not items:
            raise PublishError("this Google account has no YouTube channel; create one, then sign in again")
        return Account(
            platform=self.name,
            name=items[0]["snippet"]["title"],
            id=items[0]["id"],
            access_token=token["access_token"],
            refresh_token=token.get("refresh_token"),
            expires_at=expiry(token),
            scopes=str(token.get("scope", "")).split(),
        )

    def refresh(self, http: httpx.Client, account: Account) -> Account:
        if not account.refresh_token:
            raise PublishError("YouTube sign-in expired: run `reelhive connect youtube` again")
        client_id, secret = self.credentials()
        token = send(
            http,
            "POST",
            TOKEN,
            data={
                "client_id": client_id,
                "client_secret": secret,
                "refresh_token": account.refresh_token,
                "grant_type": "refresh_token",
            },
            what="YouTube token refresh",
        ).json()
        return account.model_copy(update={"access_token": token["access_token"], "expires_at": expiry(token)})

    def post(
        self,
        http: httpx.Client,
        account: Account,
        upload: Upload,
        copy: BaseModel,
        settings: Publishing,
        progress: Progress,
    ) -> Posted:
        assert isinstance(copy, YouTubeCopy)
        auth = {"Authorization": f"Bearer {account.access_token}"}
        options = settings.youtube
        body = {
            "snippet": {
                "title": copy.title,
                "description": copy.description,
                "tags": copy.tags,
                "categoryId": options.category_id,
                "defaultLanguage": "en",
                "defaultAudioLanguage": "en",
            },
            "status": {
                "privacyStatus": options.privacy,
                "selfDeclaredMadeForKids": False,
                "containsSyntheticMedia": settings.label_ai,
            },
        }
        session = send(
            http,
            "POST",
            f"{UPLOAD}/videos",
            params={
                "uploadType": "resumable",
                "part": "snippet,status",
                "notifySubscribers": str(options.notify_subscribers).lower(),
            },
            headers={
                **auth,
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Length": str(upload.size),
                "X-Upload-Content-Type": "video/mp4",
            },
            content=json.dumps(body),
            what="YouTube upload start",
        ).headers.get("location")
        if not session:
            raise PublishError("YouTube did not return an upload session")
        video = self._upload(http, session, auth, upload, progress)
        notes = []
        if options.privacy != "private" and video.get("status", {}).get("privacyStatus") == "private":
            notes.append("YouTube kept it private: uploads from an unaudited API project stay private until audited")
        if upload.subtitles:
            progress("Adding the caption track", None)
            try:
                self._captions(http, auth, video["id"], upload)
            except PublishError as error:  # the video is up; a retry would post it twice
                notes.append(f"Captions not added ({error}); upload video.srt in YouTube Studio")
        return Posted(id=video["id"], url=f"https://youtu.be/{video['id']}", note="; ".join(notes) or None)

    def _upload(
        self, http: httpx.Client, session: str, auth: dict[str, str], upload: Upload, progress: Progress
    ) -> dict[str, Any]:
        """PUT the file in chunks; on 308 continue from the byte YouTube says it has (its `Range`)."""
        first = 0
        while True:
            last = min(first + CHUNK, upload.size) - 1
            response = send(
                http,
                "PUT",
                session,
                ok={308},
                headers={**auth, "Content-Type": "video/mp4", "Content-Range": f"bytes {first}-{last}/{upload.size}"},
                content=read(upload.video, first, last),
                what="YouTube upload",
            )
            if response.status_code != 308:
                return response.json()
            received = response.headers.get("range")  # e.g. "bytes=0-8388607"
            first = int(received.rsplit("-", 1)[1]) + 1 if received else 0
            progress("Uploading to YouTube", first / upload.size)

    def _captions(self, http: httpx.Client, auth: dict[str, str], video_id: str, upload: Upload) -> None:
        assert upload.subtitles
        boundary = uuid.uuid4().hex
        metadata = json.dumps({"snippet": {"videoId": video_id, "language": "en", "name": "English"}})
        body = (
            (
                f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{metadata}\r\n"
                f"--{boundary}\r\nContent-Type: application/octet-stream\r\n\r\n"
            ).encode()
            + upload.subtitles.read_bytes()
            + f"\r\n--{boundary}--\r\n".encode()
        )
        send(
            http,
            "POST",
            f"{UPLOAD}/captions",
            params={"uploadType": "multipart", "part": "snippet"},
            headers={**auth, "Content-Type": f"multipart/related; boundary={boundary}"},
            content=body,
            what="YouTube captions",
        )
