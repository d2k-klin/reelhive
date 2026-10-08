"""`reelhive doctor`: is everything a run needs installed and configured?"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path

from reelhive.config import REPO_ROOT


@dataclass
class Result:
    name: str
    ok: bool
    detail: str
    required: bool = True


def _node_version() -> tuple[bool, str]:
    node = shutil.which("node")
    if not node:
        return False, "not found; install Node 20+"
    version = subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip()
    major = int(version.lstrip("v").split(".")[0] or 0)
    return major >= 20, version if major >= 20 else f"{version}; need 20+"


def _ffmpeg() -> tuple[bool, str]:
    if shutil.which("ffmpeg"):
        return True, shutil.which("ffmpeg") or ""
    if find_spec("imageio_ffmpeg"):
        return True, "bundled (imageio-ffmpeg)"
    return False, "not found; install ffmpeg"


def _espeak() -> tuple[bool, str]:
    if shutil.which("espeak-ng"):
        return True, "system espeak-ng"
    if find_spec("espeakng_loader"):
        return True, "bundled (espeakng-loader)"
    return False, "not found; install espeak-ng"


def _chrome() -> tuple[bool, str]:
    cache = Path(os.environ.get("PUPPETEER_CACHE_DIR", Path.home() / ".cache" / "puppeteer"))
    found = list((cache / "chrome-headless-shell").glob("*"))
    if found:
        return True, found[-1].name
    return False, "run: npx puppeteer browsers install chrome-headless-shell"


def run_checks() -> list[Result]:
    py_ok = (3, 11) <= sys.version_info[:2] <= (3, 12)
    credit_off = os.environ.get("REELHIVE_DISABLE_CREDIT", "").strip().lower() in ("1", "true", "yes")
    return [
        Result("python", py_ok, sys.version.split()[0] + ("" if py_ok else "; need 3.11-3.12 (Kokoro)")),
        Result("node", *_node_version()),
        Result(
            "renderer deps",
            (REPO_ROOT / "node_modules" / "@revideo" / "renderer").exists(),
            "installed" if (REPO_ROOT / "node_modules" / "@revideo").exists() else "missing; run make setup",
        ),
        Result("headless chrome", *_chrome()),
        Result("ffmpeg", *_ffmpeg()),
        Result("espeak-ng", *_espeak()),
        Result("kokoro", find_spec("kokoro") is not None, "installed" if find_spec("kokoro") else "missing"),
        Result(
            "ANTHROPIC_API_KEY",
            bool(os.environ.get("ANTHROPIC_API_KEY")),
            "set" if os.environ.get("ANTHROPIC_API_KEY") else "not set (needed for the claude provider)",
        ),
        Result(
            "credit",
            True,
            "disabled by REELHIVE_DISABLE_CREDIT" if credit_off else "on (Made with ReelHive by Mr.D)",
            required=False,
        ),
    ]
