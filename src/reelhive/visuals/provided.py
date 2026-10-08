from __future__ import annotations

import re
from pathlib import Path

import yaml
from PIL import Image

from reelhive.schemas.brief import Images


def catalog(options: Images) -> list[dict[str, str]]:
    folder = Path(options.dir).resolve()
    if not folder.is_dir():
        raise ValueError(f"image folder does not exist: {folder}")
    captions_path = Path(options.captions) if options.captions else folder / "captions.yaml"
    captions = yaml.safe_load(captions_path.read_text()) or {} if captions_path.exists() else {}
    if not isinstance(captions, dict):
        raise ValueError("captions.yaml must map filenames to descriptions")
    result = []
    for file in sorted(folder.iterdir()):
        if file.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp") or not file.is_file():
            continue
        if not file.resolve().is_relative_to(folder):
            continue
        with Image.open(file) as image:
            image.verify()
        result.append({"image": file.name, "file": str(file), "caption": str(captions.get(file.name, ""))})
    return result


def match(entries: list[dict[str, str]], filename: str | None, text: str) -> dict[str, str] | None:
    images = [entry for entry in entries if "image" in entry]
    if filename:
        return next((e for e in images if e["image"] == filename), None)
    terms = set(re.findall(r"[a-z0-9]+", text.lower()))
    scored = [
        (len(terms & set(re.findall(r"[a-z0-9]+", (e["image"] + " " + e["caption"]).lower()))), e) for e in images
    ]
    return max(scored, key=lambda pair: pair[0])[1] if any(score > 0 for score, _ in scored) else None


async def describe(ctx) -> None:
    """Opt-in only: image bytes leave the machine through the scenes provider."""
    from typing import Any

    from strands import Agent

    from reelhive.providers.factory import ProviderError

    if ctx.config.nodes.get("scenes", ctx.config.provider) == "copilot":
        raise ProviderError("Image descriptions require a Strands vision provider; set nodes.scenes to one")
    model = ctx.models.get("scenes", ctx.models.get("fast"))
    agent = Agent(
        model=model, system_prompt="Describe this image in one short factual sentence.", callback_handler=None
    )
    for entry in ctx.visual_catalog:
        if "image" not in entry:
            continue
        path = Path(entry["file"])
        format = "jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else path.suffix[1:].lower()
        content: Any = [
            {"text": "Describe this image for local matching."},
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
