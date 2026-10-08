.PHONY: setup test test-slow lint schema demo

setup:  ## Python deps, renderer deps and the headless browser Revideo renders with
	uv sync --extra dev
	npm ci
	npx puppeteer browsers install chrome-headless-shell

test:
	uv run pytest --cov --cov-report=term-missing --cov-fail-under=85
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
