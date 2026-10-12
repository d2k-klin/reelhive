"""What every platform adapter does: sign in (OAuth 2.0 with a loopback redirect), refresh, check a video against
the platform's rules, and post it with its copy."""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel

from reelhive.config import Publishing
from reelhive.publish.accounts import Account
from reelhive.publish.http import PublishError
from reelhive.schemas.publish import Platform

Progress = Callable[[str, float | None], None]  # (what is happening, share done 0-1 or None)


@dataclass(frozen=True)
class Upload:
    """The finished video as a platform sees it."""

    video: Path
    subtitles: Path | None  # SRT, uploaded as captions where the platform takes them
    size: int
    duration: float
    width: int
    height: int

    @property
    def portrait(self) -> bool:
        return self.height > self.width


@dataclass(frozen=True)
class Posted:
    id: str
    url: str | None
    note: str | None = None


class Adapter(ABC):
    name: ClassVar[Platform]
    title: ClassVar[str]
    env: ClassVar[tuple[str, str]]  # environment variables holding the client id and secret
    authorize_endpoint: ClassVar[str]
    scopes: ClassVar[tuple[str, ...]]
    scope_separator: ClassVar[str] = " "
    pkce: ClassVar[bool] = True
    client_id_param: ClassVar[str] = "client_id"
    setup: ClassVar[str]  # where to create the developer app

    def credentials(self) -> tuple[str, str]:
        client_id, secret = (os.environ.get(name, "").strip() for name in self.env)
        if not client_id or not secret:
            raise PublishError(
                f"{self.title} needs your own developer app: set {self.env[0]} and {self.env[1]} "
                f"(create one at {self.setup}). See docs/publishing.md"
            )
        return client_id, secret

    def scope_list(self, settings: Publishing) -> tuple[str, ...]:
        """The permissions to ask for; some depend on settings (e.g. posting as a page)."""
        return self.scopes

    def authorize_params(self, settings: Publishing) -> dict[str, str]:
        """Extra query parameters for the consent screen."""
        return {}

    def authorize_url(self, redirect_uri: str, state: str, challenge: str | None, settings: Publishing) -> str:
        client_id, _ = self.credentials()
        params = {
            self.client_id_param: client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
            "scope": self.scope_separator.join(self.scope_list(settings)),
            **self.authorize_params(settings),
        }
        if self.pkce and challenge:
            params |= {"code_challenge": challenge, "code_challenge_method": "S256"}
        return f"{self.authorize_endpoint}?{urlencode(params)}"

    @abstractmethod
    def exchange(self, http: httpx.Client, code: str, redirect_uri: str, verifier: str | None) -> dict[str, Any]:
        """The token response for an authorization code."""

    @abstractmethod
    def identify(self, http: httpx.Client, token: dict[str, Any], settings: Publishing) -> Account:
        """The account the token belongs to, ready to save."""

    @abstractmethod
    def refresh(self, http: httpx.Client, account: Account) -> Account:
        """A fresh access token; PublishError asking to sign in again when that isn't possible."""

    def check(self, upload: Upload, settings: Publishing) -> tuple[list[str], list[str]]:
        """(failures, warnings) for this video on this platform, before anything is sent."""
        return [], []

    @abstractmethod
    def post(
        self,
        http: httpx.Client,
        account: Account,
        upload: Upload,
        copy: BaseModel,
        settings: Publishing,
        progress: Progress,
    ) -> Posted:
        """Upload the video and publish it with `copy`."""

    def ready(self, http: httpx.Client, account: Account) -> Account:
        """The account with a usable access token (refreshed when it is about to expire)."""
        return self.refresh(http, account) if account.expiring() else account


def expiry(token: dict[str, Any], key: str = "expires_in") -> float | None:
    """Unix time a token from `token[key]` (seconds from now) expires."""
    seconds = token.get(key)
    return time.time() + float(seconds) if seconds else None
