/** @jsxImportSource @revideo/2d/lib */
import {Txt, type View2D} from '@revideo/2d';
import {easeOutCubic, waitFor} from '@revideo/core';
import type {Credit, SafeArea} from '../spec';
import {theme} from '../themes/default';

// The one place the credit text lives (plan §3.7). Python only decides mode and duration.
export const CREDIT_TEXT = 'Made with ReelHive by Mr.D';

function label(view: View2D, size: number, opacity: number) {
  return (
    <Txt text={CREDIT_TEXT} fontFamily={theme.font} fontSize={size} fill={theme.muted} opacity={opacity} />
  ) as Txt;
}

/** `end` mode: a short card after the closing scene, small text at the bottom. */
export function* creditEnd(view: View2D, credit: Credit, safe: SafeArea) {
  const node = label(view, view.width() * 0.016, 0);
  node.y(view.height() * (0.5 - safe.bottom - 0.06));
  view.add(node);
  yield* node.opacity(1, 0.3, easeOutCubic);
  yield* waitFor(Math.max(0, credit.duration - 0.3));
  node.remove();
}

/** `corner` mode: a small semi-transparent badge for the whole video. */
export function addCreditCorner(view: View2D, safe: SafeArea) {
  const node = label(view, view.width() * 0.012, 0.55);
  node.x(view.width() / 2 - view.width() * (safe.right + 0.09));
  node.y(view.height() / 2 - view.height() * (safe.bottom + 0.01));
  view.add(node);
}
