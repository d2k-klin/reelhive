.PHONY: setup test test-slow lint schema demo eval eval-baseline

setup:  ## Python deps, renderer deps and the headless browser Revideo renders with
	uv sync --extra dev $(EXTRAS)
	uv run playwright install chromium
	uv run python -c "import importlib.util, subprocess, sys; importlib.util.find_spec('copilot') and subprocess.run([sys.executable, '-m', 'copilot', 'download-runtime'], check=True)"
	npm ci
	npx puppeteer browsers install chrome-headless-shell

test:
	uv run --all-extras pytest --cov --cov-report=term-missing --cov-fail-under=85
	npm test -w renderer

test-slow:  ## real Kokoro + real render
	uv run pytest -m slow

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy
	npx -w renderer tsc --noEmit

schema:  ## regenerate renderer/src/spec.schema.json from the Pydantic models
	uv run python -m reelhive.schemas.scene_spec

demo:
	uv run reelhive run examples/briefs/small.yaml

eval:  ## compare providers on the core set (spec only: no video, no paid images); PROVIDERS=claude,bedrock
	uv run reelhive eval --providers $(or $(PROVIDERS),claude) --set core

eval-baseline:  ## record the Claude core-set baseline the eval gate compares against; commit the file
	uv run reelhive eval --providers claude --set core --save-baseline evals/baselines/claude-core.json
