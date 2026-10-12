"""The CC0 sound-effect library in assets/sfx (synthesized by scripts/make_sfx.py; nothing is generated at run time)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reelhive.config import REPO_ROOT

SFX_DIR = REPO_ROOT / "assets" / "sfx"


def load_effects(sfx_dir: Path = SFX_DIR) -> list[dict[str, Any]]:
    """Each effect: `name`, `file`, `description`, `suits` (moment kinds), `duration` and `peak` in seconds."""
    return json.loads((sfx_dir / "manifest.json").read_text())["effects"]
