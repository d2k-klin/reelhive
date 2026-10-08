# Changelog

All notable changes to ReelHive are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **M1, `small` level end to end:** `reelhive run brief.yaml` turns a brief into a narrated 16:9 MP4 with ducked background music. Two Strands graphs (draft and production) with parallel branches, a conditional `fix` path and custom deterministic nodes; Kokoro TTS; a Revideo renderer driven by a validated scene spec; the "Made with ReelHive by Mr.D" credit (end card or corner badge, `REELHIVE_DISABLE_CREDIT=true` to hide it; the metadata tag is always written); `reelhive doctor`.
- **M2, `medium` level:** script approval stop (`reelhive approve`), 9:16 and 1:1, brand colors and logo, voice accents and speed, tone, pacing, music mood and CTA URL. Providers: Claude, Bedrock, OpenAI, Ollama and GitHub Copilot (through the Copilot SDK, locked down to a single submit tool), with per-node overrides. Visual sources: provided images, masked screenshots with saved login state (`reelhive login`, `reelhive capture`), OpenAI concept generation with a cache and a cap, and `auto` fallbacks; generated images never stand in for product UI. Templates `image-full` and `screenshot-pan`.
- **M4, evals:** `reelhive eval` compares providers on a 24-brief dataset in spec-only mode (no video, no paid images), with deterministic metrics, an LLM judge with fixed rubrics, Markdown/HTML/JSON reports and a 5% regression gate (`eval-gate.yml`). Nightly slow tests and a Claude smoke eval.
- Community files, issue and PR templates, Dependabot, CODEOWNERS and a release workflow.

### Fixed
- Short videos (15-20 s) overran the duration check because the script's word target ignored per-scene padding; found by the first eval dry run.
