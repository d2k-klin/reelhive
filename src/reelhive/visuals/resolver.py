"""Resolve sources in plan order; product UI never reaches a generator."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image

from reelhive.core.context import RunContext
from reelhive.schemas.brief import Generate, Images
from reelhive.schemas.scene_spec import HookScene, HookText, Theme, VisualAsset
from reelhive.visuals import capture, provided

MINIMUM_SIZE = {"16:9": (1280, 720), "9:16": (720, 1280), "1:1": (720, 720)}
GENERATION_SIZE = {"16:9": "1536x1024", "9:16": "1024x1536", "1:1": "1024x1024"}


def local_asset(run_dir: Path, name: str) -> Path:
    path = (run_dir / name).resolve()
    if not path.is_relative_to(run_dir.resolve()):
        raise ValueError("visual file must be inside the run folder")
    return path


def image_ok(path: Path, format: str) -> bool:
    try:
        with Image.open(path) as image:
            w, h = MINIMUM_SIZE[format]
            valid = image.width >= w and image.height >= h
            image.verify()
            return valid
    except (OSError, ValueError):
        return False


def catalog(ctx: RunContext) -> list[dict[str, str]]:
    options = ctx.brief.visuals
    entries = []
    if options.source in ("auto", "images") and isinstance(options.images, Images):
        entries += provided.catalog(options.images)
    if options.source in ("auto", "screenshots") and options.screenshots:
        try:
            entries += capture.discover(options.screenshots, ctx.brief.format)
        except Exception as e:
            ctx.events.emit("node.task", node="scenes", task=f"Screenshot discovery unavailable: {e}")
    return entries


def theme_for(ctx: RunContext) -> Theme:
    theme = Theme()
    if ctx.brief.theme == "dark":
        theme.background, theme.surface = "#050505", "#171717"
    for field, color in zip(("accent", "background", "text"), ctx.brief.brand.colors, strict=False):
        setattr(theme, field, color)
    if ctx.brief.brand.logo:
        source = Path(ctx.brief.brand.logo)
        with Image.open(source) as img:
            img.verify()
        dest = ctx.path("visuals", "brand" + source.suffix.lower())
        shutil.copyfile(source, dest)
        theme.logo = str(dest.relative_to(ctx.run_dir))
    return theme


def resolve(ctx: RunContext, generator=None) -> None:
    assert ctx.spec
    generator = generator or ctx.image_generator
    options = ctx.brief.visuals
    generation = options.generate if isinstance(options.generate, Generate) else None
    cache_path = ctx.path("visuals", "generated.json")
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    for position, scene in enumerate(ctx.spec.scenes):
        request = scene.visual_request
        if request.kind == "none" or options.source == "none":
            scene.visual = None
        elif scene.visual and (request.kind != "product_ui" or scene.visual.source != "generated"):
            if image_ok(local_asset(ctx.run_dir, scene.visual.file), ctx.brief.format):
                continue
            scene.visual = None
        else:
            scene.visual = None
        if request.kind != "none" and options.source != "none" and scene.visual is None:
            if options.source in ("auto", "images"):
                entry = provided.match(ctx.visual_catalog, request.image, scene.narration + " " + scene.text.headline)
                if entry and image_ok(Path(entry["file"]), ctx.brief.format):
                    dest = ctx.path("visuals", f"scene_{scene.index:02d}_provided{Path(entry['file']).suffix.lower()}")
                    shutil.copyfile(entry["file"], dest)
                    scene.visual = VisualAsset(source="provided", file=str(dest.relative_to(ctx.run_dir)))
            if (
                scene.visual is None
                and request.kind == "product_ui"
                and options.source in ("auto", "screenshots")
                and options.screenshots
            ):
                routes = [e["route"] for e in ctx.visual_catalog if "route" in e]
                route = request.route or (routes[0] if routes else options.screenshots.url)
                dest = ctx.path("visuals", f"scene_{scene.index:02d}_screenshot.png")
                try:
                    target = capture.same_origin(options.screenshots.url, route)
                    allowed = routes or [
                        capture.same_origin(options.screenshots.url, r)
                        for r in (options.screenshots.routes or [options.screenshots.url])
                    ]
                    if target not in [capture.same_origin(options.screenshots.url, r) for r in allowed]:
                        raise ValueError("requested route is not in the screenshot catalog")
                    capture.capture(options.screenshots, ctx.brief.format, target, dest)
                    if image_ok(dest, ctx.brief.format):
                        scene.visual = VisualAsset(
                            source="screenshot",
                            file=str(dest.relative_to(ctx.run_dir)),
                            frame=options.screenshots.frame,
                        )
                except Exception as e:
                    ctx.events.emit(
                        "node.task", node="visuals", task=f"Scene {scene.index}: screenshot unavailable: {e}"
                    )
            if (
                scene.visual is None
                and request.kind == "concept"
                and options.source in ("auto", "generate")
                and generation
                and request.prompt
            ):
                prompt = (
                    f"{request.prompt}\nStyle: {generation.style}\n"
                    f"Brand colors: {', '.join(ctx.brief.brand.colors)}\n"
                    "Concept illustration only. No product interface or screenshot."
                )
                settings = ctx.config.image_generation
                key = hashlib.sha256(
                    json.dumps(
                        [prompt, GENERATION_SIZE[ctx.brief.format], settings.model if settings else None]
                    ).encode()
                ).hexdigest()
                dest = ctx.path("visuals", f"gen_{key}.png")
                if not image_ok(dest, ctx.brief.format) and key not in cache and len(cache) < generation.max_images:
                    # Record attempts before a paid call, including failures, to keep the cap strict.
                    cache[key] = {"status": "attempted"}
                    cache_path.write_text(json.dumps(cache, indent=2))
                    try:
                        if generator is None:
                            if settings is None:
                                raise ValueError("set config.yaml image_generation.model to enable generation")
                            from reelhive.visuals.generators.openai import OpenAIImageGenerator

                            generator = OpenAIImageGenerator(settings)
                        usage = generator.generate(prompt, GENERATION_SIZE[ctx.brief.format], dest)
                        cache[key] = {"status": "completed", **usage}
                        cache_path.write_text(json.dumps(cache, indent=2))
                        ctx.events.emit(
                            "node.task",
                            node="visuals",
                            task=f"Generated image for scene {scene.index}",
                            image_count=len(cache),
                            **usage,
                        )
                    except Exception as e:
                        ctx.events.emit(
                            "node.task", node="visuals", task=f"Scene {scene.index}: generation unavailable: {e}"
                        )
                if image_ok(dest, ctx.brief.format):
                    scene.visual = VisualAsset(source="generated", file=str(dest.relative_to(ctx.run_dir)))
        if scene.visual is None and scene.template in ("image-full", "screenshot-pan"):
            ctx.spec.scenes[position] = HookScene(
                **{
                    **scene.model_dump(exclude={"template", "text"}),
                    "text": HookText(headline=scene.text.headline, subline=scene.text.subline),
                }
            )
            ctx.events.emit("node.task", node="visuals", task=f"Scene {scene.index}: using text fallback")
        elif scene.visual:
            ctx.events.emit("node.task", node="visuals", task=f"Scene {scene.index}: {scene.visual.source}")
