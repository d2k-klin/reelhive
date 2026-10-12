"""One adapter per platform; see base.py for what each one implements."""

from typing import Any

from reelhive.publish.platforms.base import Adapter
from reelhive.publish.platforms.instagram import Instagram
from reelhive.publish.platforms.linkedin import LinkedIn
from reelhive.publish.platforms.tiktok import TikTok
from reelhive.publish.platforms.youtube import YouTube
from reelhive.schemas.publish import Platform

ADAPTERS: dict[Platform, Adapter] = {a.name: a for a in (YouTube(), LinkedIn(), TikTok(), Instagram())}


def overview(redirect_uri: str) -> list[dict[str, Any]]:
    """Per platform: is the developer app configured, who is signed in (never a token), and what to set up."""
    from reelhive.publish import accounts
    from reelhive.publish.http import PublishError

    result = []
    for platform, adapter in ADAPTERS.items():
        try:
            adapter.credentials()
            configured = True
        except PublishError:
            configured = False
        account = accounts.load(platform)
        result.append(
            {
                "platform": platform,
                "title": adapter.title,
                "configured": configured,
                "env": list(adapter.env),
                "setup": adapter.setup,
                "redirect_uri": redirect_uri,
                "account": account.public() if account else None,
            }
        )
    return result
