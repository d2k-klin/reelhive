"""Generate candidate illustrations from design/prompts (docs/reelhive-ui-plan.md §10.4).

Design time only, never at run time. Mascot and role prompts use the existing Mr.D artwork as a
reference image (image editing), so the character stays the same; icons are generated from text.

    uv run python scripts/generate_assets.py --dry-run
    uv run python scripts/generate_assets.py --only mr-d-thinking --count 1
"""

from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "design" / "prompts"
CANDIDATES = ROOT / "design" / "candidates"


def load_assets(only: str | None = None, file: str | None = None) -> list[dict]:
    """Every asset with its composed prompt, reference image and size."""
    base = yaml.safe_load((PROMPTS / "_style.yaml").read_text())
    assets = []
    for path in sorted(PROMPTS.glob("*.yaml")):
        if path.name.startswith("_") or (file and path.stem != file):
            continue
        group = yaml.safe_load(path.read_text())
        reference = group.get("reference", base["reference"])
        style = group.get("style_override") or base["style"]
        for item in group["assets"]:
            if only and item["name"] != only:
                continue
            assets.append(
                {
                    "name": item["name"],
                    "kind": group["kind"],
                    "prompt": f"{item['prompt'].strip()}\n\n{style.strip()}",
                    "reference": ROOT / reference if reference else None,
                    "size": group.get("size", base["size"]),
                }
            )
    return assets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", help="One asset name, e.g. mr-d-thinking")
    parser.add_argument("--file", help="One prompt file without .yaml: mascot, roles or icons")
    parser.add_argument("--count", type=int, default=4, help="Candidates per asset (default 4)")
    parser.add_argument("--model", help="Image model; default is config.yaml image_generation.model")
    parser.add_argument("--dry-run", action="store_true", help="Print the prompts; make no API call")
    args = parser.parse_args(argv)

    assets = load_assets(args.only, args.file)
    if not assets:
        print("no matching assets", file=sys.stderr)
        return 2
    if args.dry_run:
        for a in assets:
            ref = a["reference"].relative_to(ROOT) if a["reference"] else "none"
            print(f"## {a['name']} ({a['kind']}, reference: {ref}, {a['size']})\n{a['prompt']}\n")
        return 0

    sys.path.insert(0, str(ROOT / "src"))
    from openai import OpenAI

    from reelhive.config import load_config

    settings = load_config().image_generation
    model = args.model or (settings.model if settings else None)
    if not model:
        print("set config.yaml image_generation.model or pass --model", file=sys.stderr)
        return 2
    client = OpenAI()
    for a in assets:
        out = CANDIDATES / a["name"]
        out.mkdir(parents=True, exist_ok=True)
        if a["reference"]:
            with a["reference"].open("rb") as image:
                result = client.images.edit(model=model, image=image, prompt=a["prompt"], n=args.count, size=a["size"])
        else:
            result = client.images.generate(model=model, prompt=a["prompt"], n=args.count, size=a["size"])
        for i, item in enumerate(result.data or [], start=1):
            (out / f"{i}.png").write_bytes(base64.b64decode(item.b64_json or ""))
        print(f"{a['name']}: {len(result.data or [])} candidates in {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
