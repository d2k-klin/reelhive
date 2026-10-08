import type {Node, View2D} from '@revideo/2d';
import {all, easeInCubic, easeOutCubic, waitFor} from '@revideo/core';

export const IN = 0.5;
export const OUT = 0.4;

/** Fade/slide a node in, hold, fade it out: always takes exactly `duration` seconds. */
export function* playFor(view: View2D, node: Node, duration: number) {
  node.opacity(0);
  node.y(node.y() + 40);
  view.add(node);
  const hold = Math.max(0, duration - IN - OUT);
  yield* all(node.opacity(1, IN, easeOutCubic), node.y(node.y() - 40, IN, easeOutCubic));
  yield* waitFor(hold);
  yield* node.opacity(0, Math.min(OUT, duration - IN), easeInCubic);
  node.remove();
}
