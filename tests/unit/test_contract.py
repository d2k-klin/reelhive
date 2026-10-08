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
