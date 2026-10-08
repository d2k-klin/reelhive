"""Docs ship with the code: every relative link in a README or doc must resolve."""

import re

import pytest

from reelhive.config import REPO_ROOT

DOCS = [
    *REPO_ROOT.glob("*.md"),
    *(REPO_ROOT / "docs").glob("*.md"),
    REPO_ROOT / "evals/README.md",
    REPO_ROOT / "renderer/README.md",
    REPO_ROOT / "assets/music/README.md",
]


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_relative_links_resolve(doc):
    links = re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", doc.read_text())
    missing = [link for link in links if "://" not in link and not (doc.parent / link).exists()]
    assert not missing, missing


def test_demo_assets_exist_for_readme_and_release():
    for name in ("demo.gif", "demo.mp4", "brief.yaml"):
        assert (REPO_ROOT / "assets/demo" / name).stat().st_size > 0
