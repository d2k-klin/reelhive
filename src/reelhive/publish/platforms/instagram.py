"""Instagram Reels: the Instagram Graph API with Facebook Login, uploaded with a resumable upload (no public URL
needed), then published once Instagram has processed it.

Needs an Instagram Business or Creator account linked to a Facebook Page, and a Meta app with Facebook Login for
Business; the sign-in exchanges for a long-lived (60-day) token, refreshed while it is still valid.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
from pydantic import BaseModel

from reelhive.config import Publishing
from reelhive.publish import http as net
from reelhive.publish.accounts import Account
from reelhive.publish.http import PublishError, send
from reelhive.publish.platforms.base import Adapter, Posted, Progress, Upload, expiry
from reelhive.schemas.publish import InstagramCopy

VERSION = "v23.0"
GRAPH = f"https://graph.facebook.com/{VERSION}"
MAX_BYTES = 1024**3
PROCESSING_TIMEOUT = 600.0
POLL = 5.0


class Instagram(Adapter):
    name = "instagram"
    title = "Instagram"
    env = ("REELHIVE_META_APP_ID", "REELHIVE_META_APP_SECRET")
    authorize_endpoint = f"https://www.facebook.com/{VERSION}/dialog/oauth"
    scopes = (
        "instagram_basic",
        "instagram_content_publish",
        "pages_show_list",
        "pages_read_engagement",
        "business_management",
    )
    scope_separator = ","
    pkce = False
    setup = "https://developers.facebook.com/apps (use case: Manage messaging & content on Instagram)"

    def authorize_params(self, settings: Publishing) -> dict[str, str]:
        config_id = settings.instagram.config_id
        return {"config_id": config_id} if config_id else {}

    def _long_lived(self, http: httpx.Client, token: str, what: str) -> dict[str, Any]:
        client_id, secret = self.credentials()
        return send(
            http,
            "GET",
            f"{GRAPH}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": client_id,
                "client_secret": secret,
                "fb_exchange_token": token,
            },
            what=what,
        ).json()

    def exchange(self, http: httpx.Client, code: str, redirect_uri: str, verifier: str | None) -> dict[str, Any]:
        client_id, secret = self.credentials()
        short = send(
            http,
            "GET",
            f"{GRAPH}/oauth/access_token",
            params={"client_id": client_id, "client_secret": secret, "redirect_uri": redirect_uri, "code": code},
            what="Instagram sign-in",
        ).json()
        return self._long_lived(http, short["access_token"], "Instagram sign-in")

    def identify(self, http: httpx.Client, token: dict[str, Any], settings: Publishing) -> Account:
        pages = (
            send(
                http,
                "GET",
                f"{GRAPH}/me/accounts",
                params={"fields": "name,instagram_business_account{id,username}"},
                headers={"Authorization": f"Bearer {token['access_token']}"},
                what="Instagram account lookup",
            )
            .json()
            .get("data", [])
        )
        linked = [(p["name"], p["instagram_business_account"]) for p in pages if p.get("instagram_business_account")]
        wanted = settings.instagram.account
        match = next((x for x in linked if not wanted or x[1].get("username") == wanted.lstrip("@")), None)
        if match is None:
            raise PublishError(
                f"no Instagram account {wanted} on your Pages"
                if wanted
                else "no Instagram Business or Creator account is linked to a Facebook Page you manage"
            )
        page, instagram = match
        return Account(
            platform=self.name,
            name=f"@{instagram.get('username', instagram['id'])}",
            id=instagram["id"],
            access_token=token["access_token"],
            expires_at=expiry(token),
            scopes=list(self.scopes),
            extra={"page": page},
        )

    def refresh(self, http: httpx.Client, account: Account) -> Account:
        if account.expires_at is not None and account.expires_at <= time.time():
            raise PublishError(
                "Instagram sign-in expired (tokens last 60 days): run `reelhive connect instagram` again"
            )
        token = self._long_lived(http, account.access_token, "Instagram token refresh")
        return account.model_copy(update={"access_token": token["access_token"], "expires_at": expiry(token)})

    def check(self, upload: Upload, settings: Publishing) -> tuple[list[str], list[str]]:
        failures, warnings = [], []
        if not 3 <= upload.duration <= 15 * 60:
            failures.append("Instagram Reels are 3 seconds to 15 minutes")
        if upload.size > MAX_BYTES:
            failures.append("Instagram takes Reels files up to 1 GB")
        if not upload.portrait:
            warnings.append("Reels are vertical: a 16:9 or 1:1 video shows letterboxed; make a 9:16 cut for it")
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
        assert isinstance(copy, InstagramCopy)
        bearer = {"Authorization": f"Bearer {account.access_token}"}
        container = send(
            http,
            "POST",
            f"{GRAPH}/{account.id}/media",
            headers=bearer,
            data={
                "media_type": "REELS",
                "upload_type": "resumable",
                "caption": copy.caption,
                "share_to_feed": str(settings.instagram.share_to_feed).lower(),
            },
            what="Instagram upload start",
        ).json()
        progress("Uploading to Instagram", None)
        send(
            http,
            "POST",
            container["uri"],
            headers={"Authorization": f"OAuth {account.access_token}", "offset": "0", "file_size": str(upload.size)},
            content=upload.video.read_bytes(),
            what="Instagram upload",
        )
        progress("Instagram is processing the video", None)
        self._wait(http, bearer, container["id"])
        media = send(
            http,
            "POST",
            f"{GRAPH}/{account.id}/media_publish",
            headers=bearer,
            data={"creation_id": container["id"]},
            what="Instagram publish",
        ).json()["id"]
        link = send(
            http, "GET", f"{GRAPH}/{media}", params={"fields": "permalink"}, headers=bearer, what="Instagram link"
        ).json()
        return Posted(id=media, url=link.get("permalink"))

    def _wait(self, http: httpx.Client, headers: dict[str, str], container: str) -> None:
        deadline = time.monotonic() + PROCESSING_TIMEOUT
        while True:
            state = send(
                http,
                "GET",
                f"{GRAPH}/{container}",
                params={"fields": "status_code,status"},
                headers=headers,
                what="Instagram upload status",
            ).json()
            code = state.get("status_code")
            if code == "FINISHED":
                return
            if code in ("ERROR", "EXPIRED"):
                raise PublishError(f"Instagram could not process the video: {state.get('status') or code}")
            if time.monotonic() > deadline:
                raise PublishError("Instagram is still processing the video; publish again later")
            net.sleep(POLL)
