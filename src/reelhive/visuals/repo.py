"""A code repository as a source: a public GitHub repository (shallow-cloned) or a local project folder.

`read()` turns it into pages for `research` (the file tree, READMEs, docs and build manifests) and saves the
repository's own images (diagrams, screenshots) into `visuals/repo/` with a `captions.yaml`, so the scene planner
picks them like the user's image folder. Nothing in the repository runs: the clone skips hooks, submodules and LFS,
symlinks are never followed (a repository can't point the reader at files outside it), and a clone is deleted once
read. Only files named like docs or manifests are read, so `.env` files and source code stay unread.
"""

from __future__ import annotations

import os
import posixpath
import re
import subprocess
import tempfile
from pathlib import Path

import yaml
from PIL import Image

from reelhive.visuals.products import MAX_PIXELS, MIN_SIDE

MAX_WALK = 20_000  # files looked at; ponytail: a monorepo past this is read from its first 20k files
MAX_TREE = 400  # paths listed for the agents
MAX_FILES = 20
MAX_CHARS = 8000
MAX_IMAGES = 12
MAX_BYTES = 20_000_000
SKIP_DIRS = {"node_modules", "vendor", "dist", "build", "target", "out", "coverage", "__pycache__"}
DOCS = re.compile(r"(^|/)(readme|architecture|design|overview)[^/]*\.(md|rst|txt)$|^docs?/.+\.md$", re.IGNORECASE)
MANIFESTS = {
    "package.json",
    "pyproject.toml",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yaml",
    "Makefile",
}
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".gif")
MARKDOWN_IMAGE = re.compile(r"!\[([^\]]*)\]\(<?([^)\s>]+)")


def is_remote(source: str) -> bool:
    return "://" in source


def name_of(source: str) -> str:
    """`owner/name` for a URL, the folder name for a local path."""
    if is_remote(source):
        return "/".join(source.removesuffix("/").removesuffix(".git").rsplit("/", 2)[-2:])
    return Path(source).resolve().name


def clone(url: str, dest: Path) -> None:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1"}  # a private repo fails, never asks
    # ponytail: depth 1 still downloads every blob of the tip; a partial clone if huge repos matter
    command = ["git", "clone", "--depth", "1", "--single-branch", "--no-tags", "--quiet", url, str(dest)]
    done = subprocess.run(command, env=env, capture_output=True, text=True, timeout=180)
    if done.returncode:
        raise RuntimeError(done.stderr.strip().splitlines()[-1] if done.stderr.strip() else "git clone failed")


def files(root: Path) -> list[str]:
    """Regular files under `root`, relative and sorted: no symlinks, hidden files or vendored folders."""
    found: list[str] = []
    for folder, dirs, names in os.walk(root):  # followlinks=False: a linked folder is never entered
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        for name in names:
            if name.startswith("."):  # .env and friends: not even their names go out
                continue
            path = Path(folder) / name
            if not path.is_symlink() and path.is_file():
                found.append(path.relative_to(root).as_posix())
        if len(found) >= MAX_WALK:
            break
    return sorted(found)


def text_files(paths: list[str]) -> list[str]:
    """Docs and manifests worth reading, root README first, shallow before deep."""
    wanted = [p for p in paths if DOCS.search(p) or (posixpath.basename(p) in MANIFESTS and p.count("/") <= 1)]
    return sorted(wanted, key=lambda p: (not re.match(r"readme", p, re.IGNORECASE), p.count("/"), p))[:MAX_FILES]


def alt_texts(root: Path, docs: list[str]) -> dict[str, str]:
    """Image path -> its alt text, from the Markdown that shows it."""
    found: dict[str, str] = {}
    for doc in docs:
        if not doc.lower().endswith(".md"):
            continue
        for alt, target in MARKDOWN_IMAGE.findall((root / doc).read_text(errors="replace")):
            if "://" not in target:
                path = posixpath.normpath(posixpath.join(posixpath.dirname(doc), target.split("#")[0]))
                found.setdefault(path.lstrip("/"), alt.strip())
    return found


def save_images(root: Path, paths: list[str], alts: dict[str, str], folder: Path) -> tuple[int, int]:
    """Copy the repository's images that are large enough to show into `folder`, flattened onto white (diagrams
    are often transparent), images the docs show first. Returns how many were saved and how many skipped."""
    images = [p for p in paths if p.lower().endswith(IMAGE_SUFFIXES)]
    images.sort(key=lambda p: p not in alts)
    captions: dict[str, str] = {}
    skipped = 0
    for path in images:
        if len(captions) >= MAX_IMAGES:
            break
        source = root / path
        try:
            if source.stat().st_size > MAX_BYTES:
                raise ValueError("too large")
            with Image.open(source) as image:
                image.verify()
            with Image.open(source) as image:
                if min(image.size) < MIN_SIDE or image.width * image.height > MAX_PIXELS:
                    raise ValueError(f"{image.width}x{image.height}")
                rgba = image.convert("RGBA")
            canvas = Image.new("RGB", rgba.size, "white")
            canvas.paste(rgba, mask=rgba.getchannel("A"))
            name = f"repo-{len(captions) + 1}.png"
            folder.mkdir(parents=True, exist_ok=True)
            canvas.save(folder / name, "PNG")
            alt = alts.get(path)
            captions[name] = f"{alt} ({path} in the repository)" if alt else f"Image from the repository: {path}"
        except Exception:  # an icon or a broken file is skipped, the rest still count
            skipped += 1
    if captions:
        (folder / "captions.yaml").write_text(yaml.safe_dump(captions))
    return len(captions), skipped


def read(source: str, images: Path | None) -> tuple[list[dict], int, int]:
    """The repository at `source` (URL or folder) as research pages; its images go to `images` unless None.
    Returns the pages, the images saved and the images skipped."""
    with tempfile.TemporaryDirectory() as scratch:
        if is_remote(source):
            root = Path(scratch) / "repo"
            clone(source, root)
        else:
            root = Path(source).expanduser().resolve()
            if not root.is_dir():
                raise ValueError(f"repo folder does not exist: {root}")
        name = name_of(source)
        paths = files(root)
        more = f"\n... and {len(paths) - MAX_TREE} more files" if len(paths) > MAX_TREE else ""
        pages = [{"title": f"{name}: file tree", "route": name, "text": "\n".join(paths[:MAX_TREE]) + more}]
        docs = text_files(paths)
        for path in docs:
            source_file = root / path
            if source_file.stat().st_size <= MAX_BYTES:
                text = source_file.read_text(errors="replace")[:MAX_CHARS].strip()
                if text:
                    pages.append({"title": f"{name}: {path}", "route": path, "text": text})
        saved = skipped = 0
        if images is not None:
            saved, skipped = save_images(root, paths, alt_texts(root, docs), images)
        return pages, saved, skipped
