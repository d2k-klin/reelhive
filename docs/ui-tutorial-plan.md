# UI tutorial and verification plan

## Scope

Make the existing studio teach its workflow as the user works. Keep provider names only where choosing or configuring an account requires them; describe production through writing, scene design, voice, music, quality review, and video creation.

## Implementation

1. Add shared, keyboard- and touch-accessible help for unfamiliar fields and actions. Explain consequences, saving, costs, privacy, and approval requirements beside the relevant control.
2. Give Mr.D concise contextual guidance on each page and run state: what is happening, what happens next, and when the user must act. Use real run/event state, without invented progress or library names.
3. Fix workflow defects found during review: sign-in completion, unsaved scene approval, stale event state on navigation, visual request switching, hidden failures, and keyboard access to run rows.
4. Replace raw event JSON and infrastructure names in normal production views with readable status and quality results. Retain actionable provider setup and downloadable diagnostic logs.
5. Verify the actual built UI with the existing local fake-provider servers: draft/import/export, script and scene approvals, quick edits/undo, saving, image approval, navigation, failures, downloads, keyboard help, narrow layouts, and both themes. Run API and frontend regression checks, and record limitations honestly.

## Acceptance

- Help opens on hover, keyboard focus, and tap; Escape closes it.
- Mr.D explains current work and next steps, including pauses, queueing, failures, and completion.
- Visible scene edits must be saved before rendering or regeneration.
- Routine production screens do not display implementation/library names or raw JSON.
- Existing quick actions and approval workflows continue to pass; new fixes have regression coverage.

## Polish requested from screenshots

- Visual direction: a calm production workspace, compact typography, and the existing lime accent for active work.
- Content: Mr.D explains the present step; a compact title identifies the run; a five-stage production path shows the parallel work; quality checks and recovery follow.
- Interaction: help reveals on focus/hover and can be pinned by tap; only active work pulses (reduced motion respected); duration controls stay synchronized on drag, typing, and keyboard input.
- Replace the zoomable graph and repeated stage cards with an accessible, responsive ordered pipeline. Keep the original full brief available on demand.

## Implemented and verified

The shared help, Mr.D guidance, readable progress and quality checks are implemented. Follow-up review fixed the duration controls, oversized story title, mobile recovery layout, and completed stages being mislabeled after scene approval. Regression coverage also exercises the preview remount fix, save-before-approve flow, image approval reset, login completion contract, draft files, settings, and quick-action undo.

Verification uses local fake agents, stub narration, and a real browser/server with test media. It does not verify paid provider credentials, real external sign-in, image-generation billing, or full-quality voice/video production. Final checks: production build passed; 27 Playwright browser tests passed; 9 frontend unit tests passed; 26 documentation checks passed.
