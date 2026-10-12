from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from PIL import Image

from reelhive.schemas.brief import Images
from reelhive.visuals import clips

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")


def catalog(options: Images, posters: Path | None = None) -> list[dict[str, Any]]:
    """The user's images and clips. Clips list their length and size, and get a poster frame in `posters`."""
    folder = Path(options.dir).resolve()
    if not folder.is_dir():
        raise ValueError(f"image folder does not exist: {folder}")
    captions_path = Path(options.captions) if options.captions else folder / "captions.yaml"
    captions = yaml.safe_load(captions_path.read_text()) or {} if captions_path.exists() else {}
    if not isinstance(captions, dict):
        raise ValueError("captions.yaml must map filenames to descriptions")
    result = []
    for file in sorted(folder.iterdir()):
        suffix = file.suffix.lower()
        if suffix not in (*IMAGE_SUFFIXES, *clips.SUFFIXES) or not file.is_file():
            continue
        if not file.resolve().is_relative_to(folder):
            continue
        caption = str(captions.get(file.name, ""))
        if suffix in clips.SUFFIXES:
            info = clips.inspect(file)
            entry: dict[str, Any] = {"clip": file.name, "file": str(file), "caption": caption, **info}
            if posters:
                entry["poster"] = str(clips.poster(file, posters / f"{file.stem}.jpg", info["duration"] / 2))
            result.append(entry)
            continue
        with Image.open(file) as image:
            image.verify()
        result.append({"image": file.name, "file": str(file), "caption": caption})
    return result


def clip(entries: list[dict[str, Any]], filename: str) -> dict[str, Any] | None:
    """A clip only ever plays when the planner names it: it moves, so a keyword guess could show the wrong action."""
    return next((e for e in entries if e.get("clip") == filename), None)


def match(entries: list[dict[str, Any]], filename: str | None, text: str) -> dict[str, Any] | None:
    images = [entry for entry in entries if "image" in entry]
    if filename:
        return next((e for e in images if e["image"] == filename), None)
    # ponytail: document pages only by name; their captions are page text and would win every keyword match
    images = [e for e in images if "document" not in e]
    terms = set(re.findall(r"[a-z0-9]+", text.lower()))
    scored = [
        (len(terms & set(re.findall(r"[a-z0-9]+", (e["image"] + " " + e["caption"]).lower()))), e) for e in images
    ]
    return max(scored, key=lambda pair: pair[0])[1] if any(score > 0 for score, _ in scored) else None


async def describe(ctx) -> None:
    """Opt-in only: image bytes (and one frame per clip) leave the machine through the scenes provider."""
    from strands import Agent

    if ctx.config.provider_for("scenes", "fast") == "copilot":
        # Copilot is locked to text; match on filenames and captions instead of failing the run.
        ctx.events.emit(
            "node.task",
            node="scenes",
            task="Skipped image descriptions: Copilot can't read images. Set nodes.scenes to a vision provider.",
        )
        return
    model = ctx.models.get("scenes", ctx.models.get("fast"))
    agent = Agent(
        model=model, system_prompt="Describe this image in one short factual sentence.", callback_handler=None
    )
    for entry in ctx.visual_catalog:
        if "image" not in entry and "poster" not in entry:
            continue
        path = Path(entry.get("poster") or entry["file"])
        format = "jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else path.suffix[1:].lower()
        what = "frame from the middle of a video clip" if "clip" in entry else "image"
        content: Any = [
            {"text": f"Describe this {what} for local matching."},
            {"image": {"format": format, "source": {"bytes": path.read_bytes()}}},
        ]
        result = await agent.invoke_async(content)
        entry["caption"] = str(result)
        ctx.events.emit(
            "node.task",
            node="scenes",
            task=f"Described {path.name}",
            tokens=result.metrics.accumulated_usage["totalTokens"],
        )
