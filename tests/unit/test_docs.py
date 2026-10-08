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


# Folders that must not have a README: GitHub would show .github/README.md instead of the main README,
# and ISSUE_TEMPLATE would offer a README as an issue template. Skill folders are documented by SKILL.md.
NO_README = {".github", ".github/ISSUE_TEMPLATE"}
SKIP_PARTS = {
    "node_modules",
    "__pycache__",
    ".venv",
    ".git",
    "runs",
    "reports",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "graphify-out",
    "test-results",
    "playwright-report",
    ".claude/worktrees",
}


def project_folders():
    for path in sorted(p for p in REPO_ROOT.rglob("*") if p.is_dir()):
        rel = path.relative_to(REPO_ROOT).as_posix()
        if any(part in SKIP_PARTS or part.endswith(".egg-info") for part in path.relative_to(REPO_ROOT).parts):
            continue
        if rel in NO_README or (path / "SKILL.md").exists() or not any(f.is_file() for f in path.rglob("*")):
            continue
        yield rel


def test_every_project_folder_has_a_readme():
    missing = [rel for rel in project_folders() if not (REPO_ROOT / rel / "README.md").exists()]
    assert not missing, f"add a README.md (overview, contents, how to extend) to: {missing}"


def test_folder_readme_links_resolve():
    for readme in (REPO_ROOT / rel / "README.md" for rel in project_folders()):
        links = re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", readme.read_text())
        missing = [link for link in links if "://" not in link and not (readme.parent / link).exists()]
        assert not missing, (readme, missing)
