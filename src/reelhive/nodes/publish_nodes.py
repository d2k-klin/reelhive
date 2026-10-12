"""The deterministic publishing nodes: `ready` checks every chosen platform before anything is written or sent,
and one `post_<platform>` node per platform uploads and publishes, in parallel with the others."""

from __future__ import annotations

from contextlib import nullcontext
from datetime import UTC, datetime
from typing import Any, ClassVar

from reelhive.core.context import RunContext
from reelhive.nodes.base import FunctionNode
from reelhive.publish import accounts
from reelhive.publish.http import PublishError, client
from reelhive.publish.platforms import ADAPTERS
from reelhive.publish.platforms.base import Upload
from reelhive.schemas.publish import Platform, PostResult


def upload_of(ctx: RunContext) -> Upload:
    from reelhive.audio.mixer import probe

    video = ctx.run_dir / "video.mp4"
    if not video.is_file():
        raise PublishError("the run has no finished video to publish")
    info = probe(video)
    subtitles = video.with_suffix(".srt")
    return Upload(
        video=video,
        subtitles=subtitles if subtitles.is_file() else None,
        size=video.stat().st_size,
        duration=float(info["duration"]),
        width=int(info["width"]),
        height=int(info["height"]),
    )


class ReadyNode(FunctionNode):
    """Gates before any model call or upload: a finished video, the developer app's credentials in the environment,
    a signed-in account, and a video each platform accepts (length, size; orientation as a warning)."""

    name = "ready"

    def run(self, ctx: RunContext) -> None:
        assert ctx.publish
        failures, warnings = [], []
        try:
            upload: Upload | None = upload_of(ctx)
        except PublishError as e:
            upload, failures = None, [str(e)]
        settings = ctx.config.publishing
        for platform in ctx.publish.platforms:
            adapter = ADAPTERS[platform]
            problems = []
            try:
                adapter.credentials()
            except PublishError as e:
                problems.append(str(e))
            if accounts.load(platform) is None:
                problems.append(f"{adapter.title}: not signed in; run `reelhive connect {platform}`")
            if upload:
                rejected, cautions = adapter.check(upload, settings)
                problems += rejected
                warnings += cautions
            ctx.events.emit(
                "gate.result",
                node=self.name,
                check=f"{platform}_ready",
                value=not problems,
                threshold="credentials, account and video accepted",
                passed=not problems,
            )
            failures += problems
        for warning in warnings:
            ctx.events.emit("node.task", node=self.name, task=warning)
        with ctx.lock:
            ctx.publish.failures, ctx.publish.warnings = failures, warnings


class PostNode(FunctionNode):
    """Upload the video to one platform and publish it with the approved copy. A failure is recorded, not raised,
    so the other platforms finish; a platform already published is never posted twice."""

    platform: ClassVar[Platform]

    def run(self, ctx: RunContext) -> None:
        assert ctx.publish and ctx.publish.posts
        adapter = ADAPTERS[self.platform]
        done = ctx.publish.results.get(self.platform)
        if done and done.status == "published":
            ctx.events.emit("node.task", node=self.name, task=f"Already on {adapter.title}: {done.url or done.id}")
            return
        self._record(ctx, PostResult(status="publishing", at=datetime.now(UTC)))

        def progress(task: str, share: float | None) -> None:
            data: dict[str, Any] = {"node": self.name, "task": task}
            if share is not None:
                data["progress"] = round(share, 3)
            ctx.events.emit("node.task", **data)

        try:
            account = accounts.load(self.platform)
            if account is None:
                raise PublishError(f"{adapter.title}: not signed in; run `reelhive connect {self.platform}`")
            with nullcontext(ctx.http) if ctx.http else client() as http:
                fresh = adapter.ready(http, account)
                if fresh is not account:
                    accounts.save(fresh)
                posted = adapter.post(
                    http,
                    fresh,
                    upload_of(ctx),
                    getattr(ctx.publish.posts, self.platform),
                    ctx.config.publishing,
                    progress,
                )
        except Exception as e:  # one platform's failure must not stop the others
            message = str(e) if isinstance(e, PublishError) else f"{type(e).__name__}: {e}"
            self._record(ctx, PostResult(status="failed", error=message, at=datetime.now(UTC)))
            ctx.events.emit("publish.failed", platform=self.platform, error=message)
            return
        result = PostResult(status="published", id=posted.id, url=posted.url, note=posted.note, at=datetime.now(UTC))
        self._record(ctx, result)
        ctx.events.emit("publish.posted", platform=self.platform, url=posted.url, note=posted.note)

    def _record(self, ctx: RunContext, result: PostResult) -> None:
        assert ctx.publish
        with ctx.lock:
            ctx.publish.results[self.platform] = result
            ctx.save_publish()


class PostYouTube(PostNode):
    name = "post_youtube"
    platform = "youtube"


class PostLinkedIn(PostNode):
    name = "post_linkedin"
    platform = "linkedin"


class PostTikTok(PostNode):
    name = "post_tiktok"
    platform = "tiktok"


class PostInstagram(PostNode):
    name = "post_instagram"
    platform = "instagram"


POST_NODES: dict[Platform, type[PostNode]] = {
    "youtube": PostYouTube,
    "linkedin": PostLinkedIn,
    "tiktok": PostTikTok,
    "instagram": PostInstagram,
}
