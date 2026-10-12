"""`sound`: a sound designer who scores the reviewed cut with a few effects, or none.

Runs once the cut has passed review, so it scores the picture that ships. It may only place an effect on a moment
the renderer reported from its own clock (`render/layout.json`: a shot cutting in, an entrance landing, the camera
closing in on a region), and only an effect from the CC0 library that suits that kind of moment. The output model
is built for this run, so moment ids and effect names are closed sets, and the rules of restraint are validators:

* a budget of one effect per started half minute, never more than MAX_CUES;
* at least MIN_GAP seconds between effects;
* quiet (UNDER_SPEECH dB or less) wherever it overlaps the voice, and quieter still (ON_WORD) when its peak
  lands on a spoken word, so the voice always stays intelligible;
* inside the video.

A plan that breaks a rule goes back to the model as a tool error and is repaired within the same call.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator
from strands.types.event_loop import Usage

from reelhive.agents.plan import brief_block
from reelhive.audio.sfx_library import load_effects
from reelhive.core.context import RunContext
from reelhive.nodes.base import AgentNode, _no_usage
from reelhive.schemas.layout import LayoutReport
from reelhive.schemas.scene_spec import SceneSpec, SoundCue

MAX_CUES = 3
MIN_GAP = 5.0  # seconds between two effects' moments
UNDER_SPEECH = -20.0  # loudest an effect may be where it overlaps the voice
ON_WORD = -24.0  # loudest an effect may be when its peak lands on a spoken word
WORD_MARGIN = 0.08  # a peak this close to a word counts as on it
GAIN = (-30.0, -10.0)


def budget(duration: float) -> int:
    """One effect per started half minute of video, at most MAX_CUES: a 20 s video gets one, a 90 s video three."""
    return min(MAX_CUES, 1 + int(duration // 30))


@dataclass(frozen=True)
class Opening:
    """A moment an effect may score."""

    id: str
    kind: str
    at: float
    detail: str
    shot: str


def openings(report: LayoutReport) -> list[Opening]:
    result = []
    for shot in report.shots:
        name = "intro" if shot.kind == "intro" else f"scene {shot.index}"
        for moment in shot.moments:
            result.append(Opening(f"{name} {moment.kind}", moment.kind, moment.at, moment.detail, name))
    return sorted(result, key=lambda o: o.at)


def spoken(spec: SceneSpec) -> list[tuple[float, float]]:
    """Every spoken word as (start, end) on the video clock."""
    return [(s.start + w.start, s.start + w.end) for s in spec.scenes for w in s.words]


def nearest_word(at: float, words: list[tuple[float, float]]) -> float:
    """Seconds from `at` to the closest spoken word (0 inside one); infinity without narration."""
    return min((0.0 if a <= at <= b else min(abs(at - a), abs(at - b)) for a, b in words), default=float("inf"))


def plan_model(
    moments: list[Opening], effects: list[dict[str, Any]], duration: float, words: list[tuple[float, float]]
) -> type[BaseModel]:
    """The structured output for this cut: closed sets of moments and effects, and the rules as validators."""
    by_id = {m.id: m for m in moments}
    by_name = {e["name"]: e for e in effects}
    allowed = budget(duration)
    MomentId = Literal[tuple(by_id)]  # type: ignore[valid-type]
    EffectName = Literal[tuple(by_name)]  # type: ignore[valid-type]

    class SoundChoice(BaseModel):
        moment: MomentId = Field(description="Id of the moment it scores, from the moments list")  # type: ignore[valid-type]
        effect: EffectName = Field(description="Effect name from the library")  # type: ignore[valid-type]
        gain_db: float = Field(-18.0, ge=GAIN[0], le=GAIN[1], description="Level in dB; -18 is a quiet accent")
        reason: str = Field(description="What on screen this sound makes the viewer feel, in one sentence")

    class SoundPlan(BaseModel):
        cues: list[SoundChoice] = Field(
            default_factory=list, max_length=allowed, description=f"At most {allowed}; an empty list is a fine answer"
        )
        reason: str = Field(description="Why these sounds, or why none")

        @model_validator(mode="after")
        def restrained(self) -> SoundPlan:
            problems = []
            chosen = sorted(self.cues, key=lambda c: by_id[c.moment].at)
            if len({c.moment for c in chosen}) < len(chosen):
                problems.append("each moment takes at most one effect")
            for cue in chosen:
                moment, effect = by_id[cue.moment], by_name[cue.effect]
                start = moment.at - effect["peak"]
                end = start + effect["duration"]
                if moment.kind not in effect["suits"]:
                    problems.append(f"{cue.effect} does not suit a {moment.kind} moment ({cue.moment})")
                if start < 0 or end > duration:
                    problems.append(f"{cue.effect} on {cue.moment} would play outside the video")
                overlaps = any(a < end and start < b for a, b in words)
                if nearest_word(moment.at, words) < WORD_MARGIN and cue.gain_db > ON_WORD:
                    problems.append(
                        f"{cue.moment} lands on a spoken word: use {ON_WORD:g} dB or less, or a moment between phrases"
                    )
                elif overlaps and cue.gain_db > UNDER_SPEECH:
                    problems.append(
                        f"{cue.effect} on {cue.moment} plays under the voice: use {UNDER_SPEECH:g} dB or less"
                    )
            for first, second in zip(chosen, chosen[1:], strict=False):
                gap = by_id[second.moment].at - by_id[first.moment].at
                if gap < MIN_GAP:
                    problems.append(f"{first.moment} and {second.moment} are {gap:.1f}s apart; keep {MIN_GAP:g}s")
            if problems:
                raise ValueError("; ".join(problems))
            return self

    return SoundPlan


class SoundDesignerNode(AgentNode):
    name = "sound"
    tier = "fast"
    prompt = "sound_designer"

    async def execute(self, ctx: RunContext) -> Usage:
        assert ctx.spec
        ctx.spec.sound_effects = []
        if not ctx.brief.sound_effects:
            ctx.events.emit("node.task", node=self.name, task="Sound effects turned off in the brief")
            return _no_usage()
        if ctx.spec_only:
            ctx.events.emit("node.task", node=self.name, task="Spec only: no cut to score")
            return _no_usage()
        from reelhive.render.bridge import layout_path

        report = LayoutReport.model_validate_json(layout_path(ctx.path("render", "silent.mp4")).read_text())
        self.moments = openings(report)
        self.effects = load_effects()
        self.words = spoken(ctx.spec) if ctx.brief.narration else []
        if not self.moments:
            ctx.events.emit("node.task", node=self.name, task="The renderer reported no moments to score")
            return _no_usage()
        self.output = plan_model(self.moments, self.effects, ctx.spec.duration, self.words)
        return await super().execute(ctx)

    def build_prompt(self, ctx: RunContext) -> str:
        assert ctx.spec
        music = (
            f"{ctx.music.get('title', '')} ({ctx.music.get('mood', '')})" if ctx.music and ctx.spec.music else "none"
        )
        lines = []
        for m in self.moments:
            gap = nearest_word(m.at, self.words)
            voice = (
                "no narration"
                if gap == float("inf")
                else "on a word"
                if gap < WORD_MARGIN
                else f"{gap:.2f}s from speech"
            )
            lines.append(f"- {m.id}: {m.at:.2f}s, {m.kind} ({m.detail}), {voice}")
        effects = "\n".join(
            f"- {e['name']}: {e['description']}; suits {', '.join(e['suits'])}; "
            f"{e['duration']:g}s, peak at {e['peak']:g}s"
            for e in self.effects
        )
        return (
            f"{brief_block(ctx.brief)}\n\nVideo: {ctx.spec.duration:.1f}s, {len(ctx.spec.scenes)} scenes, "
            f"music: {music}, narration: {'on' if ctx.brief.narration else 'off'}.\n"
            f"Budget: at most {budget(ctx.spec.duration)} effects, at least {MIN_GAP:g}s apart.\n\n"
            f"Moments the renderer reported (the only places a sound may go):\n" + "\n".join(lines) + "\n\n"
            f"Effect library:\n{effects}"
        )

    def apply(self, ctx: RunContext, out: Any) -> None:
        assert ctx.spec
        by_id = {m.id: m for m in self.moments}
        by_name = {e["name"]: e for e in self.effects}
        cues = sorted(
            (
                SoundCue(
                    effect=by_name[c.effect]["file"],
                    moment=c.moment,
                    at=round(by_id[c.moment].at - by_name[c.effect]["peak"], 3),
                    gain_db=c.gain_db,
                )
                for c in out.cues
            ),
            key=lambda cue: cue.at,
        )
        ctx.spec.sound_effects = cues
        if cues:
            chosen = ", ".join(f"{c.effect.removesuffix('.wav')} on {c.moment}" for c in cues)
            ctx.events.emit("node.task", node=self.name, task=f"{len(cues)} sound effects: {chosen}")
        else:
            ctx.events.emit("node.task", node=self.name, task=f"No sound effects: {out.reason}")
