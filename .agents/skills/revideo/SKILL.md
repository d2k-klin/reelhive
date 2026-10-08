---
name: revideo
description: "Design, render, debug, or test programmatic videos with Revideo and TypeScript, including projects, scenes, timelines, templates, players, render subprocesses, Chrome, ffmpeg integration, and deterministic JSON-to-video contracts. Use when working with @revideo packages or spec-driven video rendering."
---

# Revideo

Use this workflow for spec-driven Revideo projects and renderers.

## Procedure

1. Inspect the exact pinned `@revideo/*` versions and nearby working templates before using an API; keep all Revideo packages on compatible versions.
2. Define a validated, versioned JSON render contract outside the renderer. Generate or test the schema from the source model when possible.
3. Map the contract to scenes through a small dispatcher. Templates should receive typed props and must not perform network or business logic.
4. Keep dimensions, frame rate, duration, transitions, safe areas, and asset resolution explicit.
5. Resolve assets before rendering. Fail with the scene and asset name when a file is missing or unsupported.
6. Run rendering behind one subprocess adapter that captures progress, stderr, exit status, cancellation, and output paths.
7. Verify the actual media with `ffprobe`; process exit success alone does not prove a valid video.

## Template Rules

- Use stable dimensions so text, images, and dynamic content cannot shift layout unexpectedly.
- Enforce text limits before rendering and test the longest supported content.
- Keep scene templates deterministic for the same spec and assets.
- Use the Revideo player for previews, but keep preview and final-render props on the same code path.

## Testing

- Unit test contract-to-props mapping and template selection.
- Typecheck and run renderer tests after contract changes.
- Keep one short real render as a slow test; assert codec, duration, streams, dimensions, and metadata.
- Record platform-specific Chrome or ffmpeg flags next to the adapter and cover them with argument tests.

## Done When

The renderer consumes one validated contract, previews match final renders, failures identify the scene, and a real short render is verified with media metadata.