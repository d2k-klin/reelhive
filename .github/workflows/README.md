# `.github/workflows`

**Overview.** CI, the eval gate, nightly checks and releases. (The rest of `.github/` holds the issue and PR templates, Dependabot and CODEOWNERS; there is deliberately no `.github/README.md`, because GitHub would show it instead of the main README.)

## What's here

| Workflow | When | What |
| --- | --- | --- |
| [`ci.yml`](ci.yml) | every push to `main`, every PR | ruff, ruff format, mypy; pytest on Python 3.11 and 3.12 with an 85% coverage gate (fakes only, no keys); renderer tsc and vitest |
| [`ci.yml`](ci.yml) `ui-e2e` job | every push and PR | builds the studio and runs Playwright against the real server: token and Origin checks, every screen in light and dark themes with axe (WCAG 2.1 A/AA), keyboard navigation |
| [`eval-gate.yml`](eval-gate.yml) | PRs touching prompts, rubrics, the eval dataset or the baseline | the core eval set on Claude vs `evals/baselines/claude-core.json`; fails on a >5% regression and fails (never skips) without the `ANTHROPIC_API_KEY` secret |
| [`nightly.yml`](nightly.yml) | 03:00 UTC daily, manual | the slow e2e tests, and a Claude smoke eval on 5 briefs |
| [`release.yml`](release.yml) | a `v*` tag | checks the tag matches `pyproject.toml`, builds the wheel, creates a GitHub Release with the CHANGELOG section, the wheel and `assets/demo/demo.mp4`. No PyPI or npm. |

## Rules

- Pin third-party actions to a full commit SHA with the version in a comment (Dependabot keeps them fresh).
- Default to `permissions: contents: read`, and widen per job only when needed (`release.yml` needs `contents: write`).
- Secrets are only `ANTHROPIC_API_KEY` (eval gate, nightly). Normal CI must stay key-free.

## Extending

New checks belong in `ci.yml` if they are fast and key-free, and in `nightly.yml` otherwise. Mirror any new local command in the `Makefile` so contributors can run what CI runs.
