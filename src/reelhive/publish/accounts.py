"""Signed-in publishing accounts, kept per machine (not per run) in `~/.reelhive/accounts/<platform>.json`.

Tokens are written with owner-only permissions and never logged, sent to a model or copied into a run folder.
`REELHIVE_HOME` moves the folder. Client ids and secrets are never stored: they come from the environment.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from pydantic import BaseModel, Field

from reelhive.schemas.publish import PLATFORMS, Platform

REFRESH_MARGIN = 300  # refresh a token this many seconds before it expires


class Account(BaseModel):
    platform: Platform
    name: str = Field(description="Who posts: channel, member, page or username, as the platform shows it")
    id: str = Field(description="The platform's id for the account (channel id, person URN, open id, IG user id)")
    access_token: str
    refresh_token: str | None = None
    expires_at: float | None = Field(None, description="Unix time the access token expires; None if it doesn't")
    refresh_expires_at: float | None = None
    scopes: list[str] = Field(default_factory=list)
    extra: dict[str, str] = Field(default_factory=dict, description="Platform specifics, e.g. the IG user's page")

    def expiring(self, now: float | None = None) -> bool:
        return self.expires_at is not None and self.expires_at - REFRESH_MARGIN <= (now or time.time())

    def public(self) -> dict[str, object]:
        """What the CLI and studio may show: never a token."""
        return {
            "platform": self.platform,
            "name": self.name,
            "id": self.id,
            "expires_at": self.expires_at,
            "refreshable": bool(self.refresh_token),
            "scopes": self.scopes,
        }


def home() -> Path:
    return Path(os.environ.get("REELHIVE_HOME") or Path.home() / ".reelhive")


def _path(platform: Platform) -> Path:
    return home() / "accounts" / f"{platform}.json"


def save(account: Account) -> Account:
    path = _path(account.platform)
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    temporary = path.with_suffix(".tmp")
    # Created owner-only from the first byte, then moved into place.
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as file:
        file.write(account.model_dump_json(indent=2))
    temporary.replace(path)
    return account


def load(platform: Platform) -> Account | None:
    path = _path(platform)
    if not path.is_file():
        return None
    return Account.model_validate(json.loads(path.read_text()))


def remove(platform: Platform) -> bool:
    path = _path(platform)
    existed = path.is_file()
    path.unlink(missing_ok=True)
    return existed


def connected() -> dict[Platform, Account]:
    return {p: a for p in PLATFORMS if (a := load(p)) is not None}
