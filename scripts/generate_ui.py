"""Generate UI transport types and validation from the canonical Python models."""
import json
import subprocess
import tempfile
from pathlib import Path

from reelhive.config import Config
from reelhive.core.workspace import Workspace
from reelhive.schemas.brief import Brief
from reelhive.server.app import create_app

root = Path(__file__).resolve().parents[1]
scratch = tempfile.TemporaryDirectory()
ws = Workspace(Config(runs_dir=Path(scratch.name)))
app = create_app(workspace=ws, token="schema-generation-only")
(root / "ui/src/api/openapi.json").write_text(json.dumps(app.openapi(), indent=2))
schema = Brief.model_json_schema()
def expand(value):
    if isinstance(value, dict):
        if "$ref" in value:
            return expand(schema["$defs"][value["$ref"].split("/")[-1]])
        return {k: expand(v) for k, v in value.items() if k != "$defs"}
    if isinstance(value, list):
        return [expand(v) for v in value]
    return value
(root / "ui/src/schemas/brief.json").write_text(json.dumps(expand(schema), indent=2))
subprocess.run([str(root / "node_modules/.bin/openapi-typescript"), "ui/src/api/openapi.json", "-o", "ui/src/api/schema.d.ts"], cwd=root, check=True)
subprocess.run(["node", "scripts/generate_zod.mjs"], cwd=root, check=True)
ws.close()

scratch.cleanup()
