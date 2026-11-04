"""A repository as a source: docs and manifests read, images saved, nothing outside the repository touched."""

import json
import subprocess

import pytest
import yaml
from PIL import Image

from reelhive.visuals import repo


@pytest.fixture
def project(tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("outside-secret-42")
    root = tmp_path / "project"
    (root / "docs").mkdir(parents=True)
    (root / "node_modules" / "dep").mkdir(parents=True)
    (root / "README.md").write_text("# Hivemind\nA queue and two workers.\n![System diagram](docs/arch.png)\n")
    (root / "docs" / "overview.md").write_text("The api writes jobs to Redis; workers drain it.")
    (root / "package.json").write_text(json.dumps({"name": "hivemind", "dependencies": {"redis": "^4"}}))
    (root / ".env").write_text("TOKEN=env-secret-7")
    (root / "src.py").write_text("print('source code is not read')")
    (root / "node_modules" / "dep" / "README.md").write_text("vendored")
    (root / "docs" / "leak.md").symlink_to(secret)
    Image.new("RGBA", (800, 800), (0, 0, 0, 0)).save(root / "docs" / "arch.png")  # a transparent diagram
    Image.new("RGB", (64, 64), "red").save(root / "icon.png")
    git = ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "add", "-A", "-f"], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "init"], check=True)
    return root


@pytest.mark.parametrize("remote", [False, True])
def test_reads_docs_and_images_and_nothing_else(project, tmp_path, remote):
    source = f"file://{project}" if remote else str(project)
    images = tmp_path / "out" / "visuals" / "repo"
    pages, saved, skipped = repo.read(source, images)

    text = "\n".join(p["text"] for p in pages)
    assert pages[0]["title"].endswith("project: file tree") and "docs/arch.png" in pages[0]["text"]
    assert [p["route"] for p in pages[1:]] == ["README.md", "package.json", "docs/overview.md"]
    assert "A queue and two workers" in text and "workers drain it" in text and '"redis"' in text
    for unread in ("outside-secret-42", "env-secret-7", "source code is not read", "vendored", ".env", "leak.md"):
        assert unread not in text
    assert (saved, skipped) == (1, 1)  # the icon is too small to show
    assert yaml.safe_load((images / "captions.yaml").read_text()) == {
        "repo-1.png": "System diagram (docs/arch.png in the repository)"
    }
    with Image.open(images / "repo-1.png") as image:
        assert image.mode == "RGB" and image.getpixel((0, 0)) == (255, 255, 255)  # flattened onto white


def test_no_images_folder_reads_text_only(project):
    pages, saved, skipped = repo.read(str(project), None)
    assert len(pages) == 4 and (saved, skipped) == (0, 0)


def test_unreachable_sources_fail_clearly(tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        repo.read(str(tmp_path / "missing"), None)
    with pytest.raises(RuntimeError):
        repo.read(f"file://{tmp_path / 'missing'}", None)


def test_name_of():
    assert repo.name_of("https://github.com/d2k-klin/reelhive.git") == "d2k-klin/reelhive"
    assert repo.name_of("https://github.com/d2k-klin/reelhive/") == "d2k-klin/reelhive"
