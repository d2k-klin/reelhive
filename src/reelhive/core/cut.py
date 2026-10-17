"""A new cut of a finished video: another format, length or platform, from the same story and material.

The cut is a new run. It starts from the parent's normalized brief with the new target applied, takes over the
parent's research (so the website isn't read twice) and its product photos, and hands the writer the parent's
script to condense instead of starting from nothing. Screenshots are captured again, at the new format's viewport.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml

from reelhive.schemas.brief import PLATFORM_DEFAULTS, Brief
from reelhive.schemas.script import Script

CUT_FILE = "cut_from.json"
SOCIAL_SECONDS = 30  # where Reels, Shorts and TikToks hold attention; a longer parent is cut down to it


def cut_brief(
    parent: Brief, platform: str | None = None, duration: int | None = None, format: str | None = None
) -> Brief:
    """The parent's brief aimed at the new target (validated like any brief). Scenes written for the parent are
    dropped: they were timed for it."""
    data = parent.model_dump(mode="json") | {"scenes": None}
    if platform:
        data |= {**PLATFORM_DEFAULTS, "platform": platform, "duration": min(parent.duration, SOCIAL_SECONDS)}
    if format:
        data["format"] = format
    if duration:
        data["duration"] = duration
    return Brief.model_validate(data)


def seed(parent: Path, child: Path) -> None:
    """Carry the parent's research, product photos and script into the new run folder."""
    script = parent / "script.json"
    if not script.exists():
        raise ValueError("the run has no script yet; a cut needs a drafted run")
    beats = Script.model_validate_json(script.read_text()).beats
    (child / CUT_FILE).write_text(
        json.dumps({"run": parent.name, "beats": [b.model_dump(mode="json") for b in beats]}, indent=2)
    )
    if (parent / "research.json").exists():
        shutil.copyfile(parent / "research.json", child / "research.json")
    if (parent / "visuals" / "product").is_dir():
        shutil.copytree(parent / "visuals" / "product", child / "visuals" / "product", dirs_exist_ok=True)


def parent_brief(parent: Path) -> Brief:
    return Brief.model_validate(yaml.safe_load((parent / "brief.yaml").read_text()))


def cut_block(run_dir: Path) -> str:
    """For the writer: the parent's script, to condense and adapt rather than start over."""
    path = run_dir / CUT_FILE
    if not path.exists():
        return ""
    beats = json.loads(path.read_text())["beats"]
    lines = "\n".join(f"{i}. [{b['role']}] {b['narration']}" for i, b in enumerate(beats, 1))
    return (
        "\n\nThis video is a new cut of a finished one, for the format, length and pacing in the brief. Its script "
        "follows. Condense and adapt it rather than starting over: keep its strongest lines, its facts and its "
        f"names, and re-pace it for this length and number of beats.\n{lines}"
    )
