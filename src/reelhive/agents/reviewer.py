"""`review`: judge the rendered cut, the way a motion designer previews representative frames.

Two layers, cheapest first, like `critic`:

1. Layout gates on `render/layout.json`, the geometry the renderer measured once each shot settled: text
   inside the safe area, nothing overlapping, type large enough for a phone, images not upscaled into blur.
   No model call.
2. Only when those pass and the brief opts in (`frame_review`), a vision agent looks at one settled still
   per shot and scores focal point, hierarchy, readability, composition and consistency. This sends the
   frames (which can show your product) to the review provider, so it is off by default.

A failure goes back to `fix` with concrete, scene-numbered reasons; the graph bounds the rounds.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from strands.types.content import ContentBlock
from strands.types.event_loop import Usage

from reelhive.agents.critic import Check
from reelhive.agents.plan import brief_block
from reelhive.core.context import RunContext
from reelhive.nodes.base import AgentNode, _no_usage
from reelhive.schemas.layout import Box, LayoutReport, ShotLayout
from reelhive.schemas.scene_spec import Intro, SceneSpec

SAFE_MARGIN = 0.04  # of each frame side: text stays inside this inset (title-safe)
MIN_TYPE = 0.022  # of the frame's short side: 24 px at 1080, readable on a phone
MAX_ZOOM = 1.35  # source pixels may be enlarged this much before they visibly soften
OVERLAP = 0.02  # share of the smaller box two elements may share before they collide
MAX_REVIEW_ROUNDS = 2  # repair rounds after a failed review before the run stops with the report
TEXT_ROLES = {"headline", "subline", "body", "label", "item", "url", "title", "tagline", "caption"}


def _name(shot: ShotLayout) -> str:
    return "intro" if shot.kind == "intro" else f"scene {shot.index}"


def _overlap(a: Box, b: Box) -> float:
    width = min(a.x + a.width, b.x + b.width) - max(a.x, b.x)
    height = min(a.y + a.height, b.y + b.height) - max(a.y, b.y)
    smaller = min(a.width * a.height, b.width * b.height)
    return max(0.0, width) * max(0.0, height) / smaller if smaller > 0 else 0.0


def layout_checks(report: LayoutReport, spec: SceneSpec) -> list[Check]:
    shots = {(s.kind, s.index): s for s in report.shots}
    expected = [("intro", 0) if isinstance(i, Intro) else ("scene", i.index) for i in spec.timeline()]
    unmeasured = [f"{k} {i}".replace("intro 0", "intro") for k, i in expected if (k, i) not in shots]
    outside, collisions, small, soft = [], [], [], []
    for shot in report.shots:
        name = _name(shot)
        left, top = shot.width * SAFE_MARGIN, shot.height * SAFE_MARGIN
        right, bottom = shot.width - left, shot.height - top
        texts = [b for b in shot.boxes if b.role in TEXT_ROLES]
        visuals = [b for b in shot.boxes if b.role == "visual"]
        for box in texts:
            if box.x < left - 1 or box.y < top - 1 or box.x + box.width > right + 1 or box.y + box.height > bottom + 1:
                outside.append(f"{name} {box.role}")
            if box.font_size is not None and box.font_size < MIN_TYPE * min(shot.width, shot.height):
                small.append(f"{name} {box.role} ({box.font_size:.0f}px)")
        for box in visuals:
            if box.x < -1 or box.y < -1 or box.x + box.width > shot.width + 1 or box.y + box.height > shot.height + 1:
                outside.append(f"{name} visual")
        for n, a in enumerate(texts):
            for b in texts[n + 1 :] + visuals:
                if _overlap(a, b) > OVERLAP:
                    collisions.append(f"{name} {a.role}/{b.role}")
        if shot.zoom > MAX_ZOOM:
            soft.append(f"{name} ({shot.zoom:.2f}x)")
    return [
        Check(
            "measured",
            not unmeasured,
            "every shot measured",
            not unmeasured,
            f"the renderer did not report: {unmeasured}",
        ),
        Check(
            "safe_area",
            not outside,
            f"text inside a {SAFE_MARGIN:.0%} margin",
            not outside,
            f"elements run outside the frame's safe area, shorten the text or change the layout: {outside}",
        ),
        Check(
            "overlap",
            not collisions,
            "no colliding elements",
            not collisions,
            f"elements overlap, shorten the text or change the layout: {collisions}",
        ),
        Check(
            "type_size",
            not small,
            f"text at least {MIN_TYPE:.1%} of the short side",
            not small,
            f"text too small to read on a phone, use fewer words so it can be set larger: {small}",
        ),
        Check(
            "sharpness",
            not soft,
            f"images enlarged at most {MAX_ZOOM}x",
            not soft,
            f"images enlarged until they blur, close in on a larger region or show the whole page: {soft}",
        ),
    ]


class FrameVerdict(BaseModel):
    focal_point: int = Field(ge=1, le=5, description="Each frame has one clear thing to look at")
    hierarchy: int = Field(ge=1, le=5, description="Headline, supporting text and labels read in a clear order")
    readability: int = Field(ge=1, le=5, description="Text is legible at phone size, with enough contrast")
    composition: int = Field(ge=1, le=5, description="Balanced, with comfortable margins; nothing cramped or empty")
    consistency: int = Field(ge=1, le=5, description="The frames look like parts of one piece")
    passed: bool
    reasons: list[str] = Field(
        default_factory=list, description="Concrete fixes when not passed, each naming its scene: 'Scene 3: ...'"
    )


class ReviewNode(AgentNode):
    name = "review"
    tier = "strong"
    prompt = "reviewer"
    output = FrameVerdict

    async def execute(self, ctx: RunContext) -> Usage:
        assert ctx.spec
        if ctx.spec_only:
            ctx.events.emit("node.task", node=self.name, task="Spec only: no frames to review")
            ctx.review_passed = True
            return _no_usage()
        from reelhive.render.bridge import layout_path

        report = LayoutReport.model_validate_json(layout_path(ctx.path("render", "silent.mp4")).read_text())
        failures = []
        for c in layout_checks(report, ctx.spec):
            ctx.events.emit(
                "gate.result", node=self.name, check=c.name, value=c.value, threshold=c.threshold, passed=c.passed
            )
            if not c.passed:
                failures.append(c.message)
        if failures:  # geometry failed: repair before spending a token on taste
            self.conclude(ctx, failures)
            return _no_usage()
        if not ctx.brief.frame_review:
            ctx.events.emit("node.task", node=self.name, task="Layout checks passed; frame review is off")
            self.conclude(ctx, [])
            return _no_usage()
        if ctx.config.provider_for(self.name, self.tier) == "copilot":
            ctx.events.emit(
                "node.task",
                node=self.name,
                task="Skipped the frame review: Copilot can't read images. Set nodes.review to a vision provider.",
            )
            self.conclude(ctx, [])
            return _no_usage()
        from reelhive.render.frames import keyframes

        self.frames = keyframes(ctx.path("render", "silent.mp4"), ctx.spec, ctx.run_dir / "render" / "frames")
        ctx.events.emit("node.task", node=self.name, task=f"Reviewing {len(self.frames)} frames")
        return await super().execute(ctx)

    def build_prompt(self, ctx: RunContext) -> list[ContentBlock]:
        assert ctx.spec
        scenes = {s.index: s for s in ctx.spec.scenes}
        content: list[ContentBlock] = [
            {
                "text": f"{brief_block(ctx.brief)}\n\nOne settled frame per shot follows, in playing order "
                f"({ctx.spec.width}x{ctx.spec.height}). Judge them as one piece."
            }
        ]
        for kind, index, file in self.frames:
            if kind == "intro":
                caption = "Intro screen (product name and tagline)"
            else:
                scene = scenes[index]
                caption = (
                    f"Scene {index} [{scene.template}], on screen: {scene.text.model_dump_json(exclude_none=True)}"
                )
            content.append({"text": caption})
            content.append({"image": {"format": "jpeg", "source": {"bytes": file.read_bytes()}}})
        return content

    def apply(self, ctx: RunContext, out: FrameVerdict) -> None:
        scores = out.model_dump(exclude={"passed", "reasons"})
        passed = out.passed and min(scores.values()) >= 3
        ctx.events.emit("review.verdict", node=self.name, scores=scores, passed=passed, reasons=out.reasons)
        self.conclude(ctx, [] if passed else (out.reasons or ["frame review score below 3"]))

    def conclude(self, ctx: RunContext, failures: list[str]) -> None:
        """Record the verdict. A failure reopens the repair path so `fix`, `recheck` and `render` run again; the
        new render in turn reopens this node (see RenderNode)."""
        ctx.review_passed = not failures
        ctx.failures = failures
        if failures:
            ctx.review_rounds += 1
            ctx.completed.difference_update({"fix", "recheck", "render"})
            if ctx.review_rounds > MAX_REVIEW_ROUNDS:
                ctx.events.emit(
                    "node.task", node=self.name, task=f"Review still failing after {MAX_REVIEW_ROUNDS} repair rounds"
                )
