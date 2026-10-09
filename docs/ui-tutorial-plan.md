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
