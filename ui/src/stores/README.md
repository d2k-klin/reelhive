# `ui/src/stores`

**Overview.** Client state that isn't server data: the live event stream of a run.

## What's here

| File | What it is |
| --- | --- |
| [`events.ts`](events.ts) | `createEventStore()`: a Zustand store that folds the server-sent events into per-node state (status, streamed text, tasks, seconds, tokens). It remembers the last event id, so a reconnect resumes with `?after=<id>` and never applies an event twice. |
| [`events.test.ts`](events.test.ts) | vitest: events are applied in order, duplicates are ignored |

## Extending

To show a new event type (for example `suggestion.applied` from M6), handle it in `accept()` and add a test with a short event sequence. Keep the reducer pure and bounded: it already caps text, tasks and the event list.
