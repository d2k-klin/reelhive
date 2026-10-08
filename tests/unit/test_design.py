"""The design prompts are well formed and cover what the UI plan asks for (§10)."""

import importlib.util

from reelhive.config import REPO_ROOT
from reelhive.graphs.production import NODES

spec = importlib.util.spec_from_file_location("generate_assets", REPO_ROOT / "scripts/generate_assets.py")
generate_assets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generate_assets)


def test_prompts_compose_with_the_shared_style_and_reference():
    assets = generate_assets.load_assets()
    names = [a["name"] for a in assets]
    assert len(names) == len(set(names))
    mascot = next(a for a in assets if a["name"] == "mr-d-thinking")
    assert "letter D" in mascot["prompt"] and mascot["reference"].exists()
    icon = next(a for a in assets if a["kind"] == "icon")
    assert icon["reference"] is None and "Mr.D" not in icon["prompt"]


def test_every_node_and_the_editor_have_a_role_portrait_prompt():
    roles = {a["name"] for a in generate_assets.load_assets(file="roles")}
    assert {f"role-{n}" for n in ("brief", "script", *NODES, "suggest")} <= roles


def test_dry_run_prints_without_calling_an_api(capsys):
    assert generate_assets.main(["--dry-run", "--only", "role-critic"]) == 0
    out = capsys.readouterr().out
    assert "## role-critic (role" in out and "magnifying glass" in out
    assert generate_assets.main(["--dry-run", "--only", "nope"]) == 2
