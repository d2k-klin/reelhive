// The motion language: one set of easings and entrance rules every shot shares, so the video moves like one
// piece. Durations are always exact (no physics that settles "whenever"), because every shot is timed to its
// narration to the frame.
import type {Layout} from '@revideo/2d';
import {all, delay, easeInCubic, easeOutCubic, type ThreadGenerator, waitFor} from '@revideo/core';

/** A damped spring as an easing curve: a ~9% overshoot that lands exactly at t = 1. */
export function spring(t: number): number {
  const w = 11, z = 0.6, wd = w * Math.sqrt(1 - z * z);
  const f = (x: number) => 1 - Math.exp(-z * w * x) * (Math.cos(wd * x) + ((z * w) / wd) * Math.sin(wd * x));
  return f(t) / f(1);
}

/** Smooth start and stop for camera moves; no overshoot, so a close-up never bounces. */
export function glide(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

/** Runs `task`, then waits out the rest, so the whole thing takes exactly `seconds`. */
export function* exactly(seconds: number, task: ThreadGenerator): ThreadGenerator {
  yield* all(task, waitFor(seconds));
}

/** Elements arrive in reading order: each rises a little and fades in, staggered so the last lands on time. */
export function* reveal(parts: Layout[], seconds: number, rise: number): ThreadGenerator {
  if (!parts.length) return yield* waitFor(seconds);
  const each = Math.min(0.55, seconds * 0.7);
  const step = parts.length > 1 ? (seconds - each) / (parts.length - 1) : 0;
  for (const part of parts) {
    part.opacity(0);
    part.y(part.y() + rise);
  }
  yield* exactly(
    seconds,
    all(
      ...parts.map((part, i) =>
        delay(i * step, all(part.opacity(1, each, easeOutCubic), part.y(part.y() - rise, each, spring))),
      ),
    ),
  );
}

export {easeInCubic, easeOutCubic};
