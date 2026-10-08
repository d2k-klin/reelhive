"""Serve the built studio for Playwright: a throwaway workspace and a fixed test token, on 127.0.0.1 only."""

import sys
import tempfile
from pathlib import Path

import uvicorn

from reelhive.config import Config
from reelhive.server.app import create_app

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8799
with tempfile.TemporaryDirectory() as runs:
    app = create_app(Config(runs_dir=Path(runs)), token="e2e-token")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
