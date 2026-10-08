# `.agents/skills`

**Overview.** Project skills for coding agents (Codex, Copilot, Claude and others): short, task-focused procedures for the libraries ReelHive builds on. Each skill lives in its own folder as a `SKILL.md` with a name and description in its front matter; that file is the skill's documentation, so the folders have no separate README.

## What's here

| Skill | Use it when working on |
| --- | --- |
| [`strands-graph`](strands-graph/SKILL.md) | graphs, nodes, edges, shared state |
| [`kokoro-tts`](kokoro-tts/SKILL.md) | speech synthesis |
| [`revideo`](revideo/SKILL.md) | the renderer and templates |
| [`ffmpeg-media`](ffmpeg-media/SKILL.md) | mixing, ducking, muxing, probing |
| [`playwright-capture`](playwright-capture/SKILL.md) | screenshots, login, masking |
| [`github-copilot-sdk`](github-copilot-sdk/SKILL.md) | the Copilot provider |
| [`fastapi-local-server`](fastapi-local-server/SKILL.md) | the local UI's API server |
| [`react-vite-ui`](react-vite-ui/SKILL.md) | the local UI |
| [`copilotkit-ag-ui`](copilotkit-ag-ui/SKILL.md) | M6 quick actions |

These are the canonical copies; [`.claude/skills`](../../.claude/skills) holds thin pointers to them for Claude Code.

## Extending

Add `<name>/SKILL.md` with `name` and `description` front matter (the description says *when* to use it), keep it procedural and repo-specific, add a pointer in `.claude/skills/<name>/SKILL.md`, and list it here.
