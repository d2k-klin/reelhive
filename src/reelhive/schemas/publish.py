"""Publishing: the post copy per platform, and the state of a run's publishing job (`publish/job.json`).

The copy limits are each platform's own, enforced here, so the `publish` agent repairs copy that doesn't fit
inside its own structured-output call and an edit in the studio is checked the same way.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Platform = Literal["youtube", "linkedin", "tiktok", "instagram"]
PLATFORMS: tuple[Platform, ...] = ("youtube", "linkedin", "tiktok", "instagram")
HASHTAG = re.compile(r"(?<![\w#])#(\w+)", re.UNICODE)
MENTION = re.compile(r"(?<![\w@])@([\w.]+)", re.UNICODE)


def utf16_length(text: str) -> int:
    """TikTok counts UTF-16 code units, so an emoji can count twice."""
    return len(text.encode("utf-16-le")) // 2


class _Copy(BaseModel):
    model_config = ConfigDict(extra="forbid")


class YouTubeCopy(_Copy):
    title: str = Field(min_length=1, max_length=100, description="Video title: what it is and why to watch")
    description: str = Field(
        max_length=5000, description="First two lines carry the hook and the link; then the details. No < or >"
    )
    tags: list[str] = Field(default_factory=list, max_length=15, description="Search tags, without #")

    @field_validator("title", "description")
    @classmethod
    def no_angle_brackets(cls, value: str) -> str:
        if "<" in value or ">" in value:
            raise ValueError("YouTube rejects < and > in titles and descriptions")
        return value

    @field_validator("tags")
    @classmethod
    def tag_budget(cls, value: list[str]) -> list[str]:
        if any(len(tag) > 30 or "," in tag or tag.startswith("#") for tag in value):
            raise ValueError("each tag is at most 30 characters, without # or commas")
        if sum(len(tag) + 1 for tag in value) > 450:
            raise ValueError("tags must fit 450 characters together")
        return value


class LinkedInCopy(_Copy):
    commentary: str = Field(
        min_length=1, max_length=2800, description="The post text; a hook line first; up to 3 #hashtags at the end"
    )
    title: str = Field(min_length=1, max_length=100, description="The video's title, shown with the player")

    @field_validator("commentary")
    @classmethod
    def few_hashtags(cls, value: str) -> str:
        if len(HASHTAG.findall(value)) > 5:
            raise ValueError("use at most 5 hashtags on LinkedIn")
        return value


class TikTokCopy(_Copy):
    caption: str = Field(min_length=1, description="Caption with 3-5 #hashtags; at most 2200 UTF-16 units")

    @field_validator("caption")
    @classmethod
    def fits(cls, value: str) -> str:
        if utf16_length(value) > 2200:
            raise ValueError("TikTok captions are at most 2200 UTF-16 units")
        return value


class InstagramCopy(_Copy):
    caption: str = Field(min_length=1, max_length=2200, description="Reel caption: a hook line, then #hashtags")

    @field_validator("caption")
    @classmethod
    def instagram_limits(cls, value: str) -> str:
        if len(HASHTAG.findall(value)) > 30:
            raise ValueError("Instagram allows at most 30 hashtags")
        if len(MENTION.findall(value)) > 20:
            raise ValueError("Instagram allows at most 20 @mentions")
        return value


COPY_MODELS: dict[Platform, type[_Copy]] = {
    "youtube": YouTubeCopy,
    "linkedin": LinkedInCopy,
    "tiktok": TikTokCopy,
    "instagram": InstagramCopy,
}


class PostCopy(_Copy):
    """The words that go out with the video, one block per platform."""

    youtube: YouTubeCopy | None = None
    linkedin: LinkedInCopy | None = None
    tiktok: TikTokCopy | None = None
    instagram: InstagramCopy | None = None

    def platforms(self) -> list[Platform]:
        return [p for p in PLATFORMS if getattr(self, p) is not None]


PostStatus = Literal["waiting", "publishing", "published", "failed"]


class PostResult(BaseModel):
    status: PostStatus = "waiting"
    id: str | None = Field(None, description="The platform's id for the post or video")
    url: str | None = Field(None, description="Where the post can be seen")
    note: str | None = Field(None, description="Visibility notes, e.g. private until the app is audited")
    error: str | None = None
    at: datetime | None = None


JobStatus = Literal["blocked", "awaiting_approval", "publishing", "published", "partial", "failed"]


class PublishJob(BaseModel):
    """A run's publishing: which platforms, the copy, the gates' verdict, and what each post became."""

    platforms: list[Platform] = Field(min_length=1)
    status: JobStatus = "awaiting_approval"
    posts: PostCopy | None = Field(None, description="The copy per platform, written by the `publish` agent")
    failures: list[str] = Field(default_factory=list, description="Why the job can't be published yet")
    warnings: list[str] = Field(default_factory=list, description="Things that will publish but look off")
    results: dict[Platform, PostResult] = Field(
        default_factory=dict, description="Per platform, including posts that went live in an earlier job"
    )

    @field_validator("platforms")
    @classmethod
    def unique(cls, value: list[Platform]) -> list[Platform]:
        return [p for p in PLATFORMS if p in value]

    @model_validator(mode="after")
    def copy_matches(self) -> PublishJob:
        if self.posts is not None and set(self.posts.platforms()) != set(self.platforms):
            raise ValueError("copy must have exactly one block per chosen platform")
        return self

    def settle(self) -> None:
        """The job's status from its posts, once publishing has run."""
        states = [self.results.get(p, PostResult()).status for p in self.platforms]
        if all(state == "published" for state in states):
            self.status = "published"
        elif "published" in states:
            self.status = "partial"
        elif "failed" in states:
            self.status = "failed"
