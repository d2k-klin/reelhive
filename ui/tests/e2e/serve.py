"""Serve the built studio for Playwright: a throwaway workspace and a fixed test token, on 127.0.0.1 only.

python ui/tests/e2e/serve.py 8799          # empty workspace
python ui/tests/e2e/serve.py 8798 --fake   # fake models + a medium run paused at the script and a high run at
                                           # the scenes, for the M6 quick-action flow (no API key, no Kokoro)
"""

import json
import shutil
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
    workspace = Workspace(config, config_path=Path(runs) / "settings.yaml")
    if fake:
        import yaml

        sys.path.insert(0, str(REPO_ROOT / "tests"))
        from conftest import VERDICT_PASS, FakeModel, StubTTS, make_plan, make_script, stub_renderer

        from reelhive.schemas.brief import Brief

        brief = Brief.model_validate(yaml.safe_load((REPO_ROOT / "examples/briefs/low.yaml").read_text()))
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

        class StudioModel(FakeModel):
            async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
                if tool_specs[0]["name"] == "ScenePlan":
                    plan = one if "Regenerate exactly this one scene" in str(messages) else make_plan(brief)
                    scene_model = FakeModel({"ScenePlan": plan})
                    async for event in scene_model.stream(messages, tool_specs, system_prompt, **kwargs):
                        yield event
                else:
                    async for event in super().stream(messages, tool_specs, system_prompt, **kwargs):
                        yield event

        model = StudioModel(
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
        medium = seed.run(brief.model_copy(update={"level": "medium"}))  # paused at the script
        high = seed.run(brief.model_copy(update={"level": "high"}))
        seed.approve(high.run_dir)  # paused at the scenes
        workspace.close()
        for name, source, status in [
            ("tutorial-scenes", high.run_dir, "awaiting_scenes"),
            ("tutorial-images", high.run_dir, "awaiting_scenes"),
            ("tutorial-low-images", high.run_dir, "stopped"),
            ("tutorial-medium-images", high.run_dir, "stopped"),
            ("tutorial-script", medium.run_dir, "awaiting_script"),
            ("tutorial-failed", high.run_dir, "failed"),
            ("tutorial-stopped", high.run_dir, "stopped"),
            ("tutorial-done", high.run_dir, "done"),
        ]:
            target = Path(runs) / name
            shutil.copytree(source, target)
            (target / "status.json").write_text(json.dumps({"status": status}))
            if name in {"tutorial-images", "tutorial-low-images", "tutorial-medium-images"}:
                shutil.copyfile(REPO_ROOT / "docs/ui-guide/01-new-video.png", target / "sample.png")
                checkpoint = json.loads((target / "checkpoint.json").read_text())
                scene = checkpoint["spec"]["scenes"][0]
                scene["visual_request"] = {"kind": "concept", "prompt": "A video studio"}
                scene["visual"] = {"file": "sample.png", "source": "provided", "frame": "none"}
                scene["image_approved"] = False
                (target / "checkpoint.json").write_text(json.dumps(checkpoint))
                (target / "spec.json").write_text(json.dumps(checkpoint["spec"]))
                image_brief = yaml.safe_load((target / "brief.yaml").read_text())
                if name != "tutorial-images":
                    image_brief["level"] = "low" if name == "tutorial-low-images" else "medium"
                image_brief["visuals"] = {"source": "images", "images": {"dir": str(target)}}  # needs its folder
                (target / "brief.yaml").write_text(yaml.safe_dump(image_brief))
            if status == "done":
                shutil.copyfile(REPO_ROOT / "assets/demo/demo.mp4", target / "video.mp4")
        workspace = Workspace(config, config_path=Path(runs) / "settings.yaml", service_factory=service)
    app = create_app(config, token="e2e-token", workspace=workspace)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
