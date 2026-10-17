"""Python and the renderer agree on the render contract."""

import json
from hashlib import sha256

from reelhive.config import REPO_ROOT
from reelhive.schemas.scene_spec import CREDIT_TEXT, SceneSpec


def test_committed_json_schema_matches_pydantic():
    committed = json.loads((REPO_ROOT / "renderer/src/spec.schema.json").read_text())
    assert committed == SceneSpec.model_json_schema(), "run `make schema` and commit the result"


def test_credit_text_lives_in_one_renderer_constant():
    source = (REPO_ROOT / "renderer/src/templates/credit.tsx").read_text()
    assert f"export const CREDIT_TEXT = '{CREDIT_TEXT}';" in source


def test_brand_manifest_matches_shipped_webp_assets():
    root = REPO_ROOT / "assets/brand"
    manifest = json.loads((root / "manifest.json").read_text())
    assert sum((root / name).stat().st_size for name in manifest["files"]) < 2 * 1024 * 1024
    for name, record in manifest["files"].items():
        assert sha256((root / name).read_bytes()).hexdigest() == record["sha256"]


def test_layout_report_shape_matches_the_renderer():
    import re
    from typing import get_args

    from reelhive.agents.reviewer import MAX_ZOOM
    from reelhive.schemas.layout import LAYOUT_MARKER, Box

    measure = (REPO_ROOT / "renderer/src/measure.ts").read_text()
    assert f"export const LAYOUT_MARKER = '{LAYOUT_MARKER}';" in measure
    union = re.search(r"export type Role = ([^;]+);", measure)
    assert union and set(re.findall(r"'([a-z]+)'", union[1])) == set(get_args(Box.model_fields["role"].annotation))
    # The camera never enlarges past what the review gate accepts.
    device = (REPO_ROOT / "renderer/src/components/device.tsx").read_text()
    sharpness = re.search(r"export const MAX_SHARPNESS = ([\d.]+);", device)
    assert sharpness and float(sharpness[1]) <= MAX_ZOOM


def test_the_studio_names_every_check_the_critic_and_the_review_emit(brief):
    from reelhive.agents.critic import hard_checks
    from reelhive.agents.reviewer import layout_checks
    from reelhive.schemas.layout import LayoutReport
    from reelhive.schemas.scene_spec import HookScene, HookText

    brief.level = "high"  # the level with every check, image approval included
    spec = SceneSpec(scenes=[HookScene(index=1, narration="x", text=HookText(headline="h"))])
    names = {c.name for c in hard_checks(spec, brief, {})} | {c.name for c in layout_checks(LayoutReport(), spec)}
    source = (REPO_ROOT / "ui/src/components/ProductionProgress.tsx").read_text()
    unnamed = sorted(name for name in names if f"{name}:'" not in source)
    assert not unnamed, f"label these in ProductionProgress.tsx, or the studio calls them 'Production check': {unnamed}"
