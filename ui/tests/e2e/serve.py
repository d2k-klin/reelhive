"""Serve the built studio for Playwright: a throwaway workspace and a fixed test token, on 127.0.0.1 only.

python ui/tests/e2e/serve.py 8799          # empty workspace
python ui/tests/e2e/serve.py 8798 --fake   # fake models + a medium run paused at the script and a high run at
                                           # the scenes, for the M6 quick-action flow (no API key, no Kokoro)
"""

import sys
import tempfile
from pathlib import Path

import uvicorn

from reelhive.config import REPO_ROOT, Config
from reelhive.core.service import Service
from reelhive.core.workspace import Workspace
from reelhive.server.app import create_app

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8799
fake = "--fake" in sys.argv

with tempfile.TemporaryDirectory() as runs:
    config = Config(runs_dir=Path(runs))
    workspace = None
    if fake:
        import yaml

        sys.path.insert(0, str(REPO_ROOT / "tests"))
        from conftest import VERDICT_PASS, FakeModel, StubTTS, make_plan, make_script, stub_renderer

        from reelhive.schemas.brief import Brief

        brief = Brief.model_validate(yaml.safe_load((REPO_ROOT / "examples/briefs/small.yaml").read_text()))
        suggestions = {
            "suggestions": [
                {"label": "Punchier hook", "instruction": "Open with the monthly cost number and cut the warm-up."},
                {"label": "Shorten by ~2s", "instruction": "Cut about five spoken words and keep the product name."},
                {"label": "Simpler wording", "instruction": "Use everyday words a platform engineer would say aloud."},
            ]
        }
        rewritten = make_script(brief)
        rewritten["beats"][0]["narration"] = rewritten["beats"][0]["narration"].replace("word", "rewritten", 3)
        one = {"scenes": [{"template": "hook", "headline": "Cloud bills, explained", "secondary": "A shorter hook"}]}
        model = FakeModel(
            {
                "Script": [make_script(brief)] * 2 + [rewritten] * 20,  # two seed runs, then regenerations
                "Suggestions": [suggestions] * 100,
                "ScenePlan": [make_plan(brief), one] + [one] * 20,
                "MusicChoice": [{"mood": "tech", "bpm": 110, "reason": "fits"}] * 5,
                "Verdict": [VERDICT_PASS] * 5,
            }
        )

        def service(c: Config) -> Service:
            return Service(c, {"strong": model, "fast": model}, StubTTS(), stub_renderer)

        seed = service(config)
        seed.run(brief.model_copy(update={"level": "medium"}))  # paused at the script
        high = seed.run(brief.model_copy(update={"level": "high"}))
        seed.approve(high.run_dir)  # paused at the scenes
        workspace = Workspace(config, service_factory=service)
    app = create_app(config, token="e2e-token", workspace=workspace)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
