// Frame geometry: the safe content box, the type scale and text helpers. Every template places its elements
// through these, so margins, sizes and hierarchy are the same in every shot and every format.
import {Txt, type View2D} from '@revideo/2d';
import {DEFAULT} from '@revideo/core';
import type {SafeArea} from './spec';
import type {Theme} from './themes/default';

/** Title-safe on every side: the review gate's default. */
export const TITLE_SAFE: SafeArea = {top: 0.04, right: 0.04, bottom: 0.04, left: 0.04};
/** Room the layout keeps inside the safe area, so a shot passes the gate with margin to spare. */
const ROOM = {x: 0.03, y: 0.04};

export interface Stage {
  view: View2D;
  w: number;
  h: number;
  /** The short side; type and spacing scale with it so a portrait cut stays readable on a phone. */
  s: number;
  portrait: boolean;
  /** The content box, inside the title-safe margins the review gate checks with room to spare. Shots are laid
   *  out around its centre `cy` (0 unless the caption band takes the bottom of the frame). */
  content: {w: number; h: number; left: number; top: number; cy: number};
  /** The caption band below the content when captions are on: its centre and height. */
  captions: {cy: number; h: number} | null;
  /** Where text may go, as fractions of the frame (the same insets the layout gate checks). */
  safe: SafeArea;
  /** Comfortable line length for centred text. */
  measure: number;
  type: {display: number; hero: number; headline: number; body: number; label: number; url: number};
  theme: Theme;
}

export function stageOf(view: View2D, theme: Theme, captions = false, safe: SafeArea = TITLE_SAFE): Stage {
  const w = view.width(), h = view.height(), s = Math.min(w, h);
  const band = captions ? s * 0.16 : 0;
  // ponytail: the sides take the wider inset, so every template stays centred; a platform's right-hand buttons
  // cost the left a few percent of width.
  const side = Math.max(safe.left, safe.right) + ROOM.x;
  const top = safe.top + ROOM.y, bottom = safe.bottom + ROOM.y;
  const bandBottom = h / 2 - bottom * h; // the content (and the caption band under it) ends here
  const content = {
    w: w * (1 - 2 * side), h: h * (1 - top - bottom) - band, left: -w * (0.5 - side), top: -h * (0.5 - top),
    cy: (h * (top - bottom) - band) / 2,
  };
  return {
    view, w, h, s, theme, safe,
    captions: captions ? {cy: bandBottom - band / 2, h: band} : null,
    portrait: h > w,
    content,
    measure: Math.min(content.w, s * 1.3),
    type: {display: s * 0.12, hero: s * 0.078, headline: s * 0.058, body: s * 0.033, label: s * 0.024, url: s * 0.026},
  };
}

export interface TextStyle {
  size: number;
  width: number;
  weight?: number;
  color?: string;
  align?: 'left' | 'center';
  spacing?: number;
}

/** A wrapped text block of a fixed width. It is its own layout root, so it can be placed and animated freely. */
export function text(stage: Stage, value: string, style: TextStyle): Txt {
  return new Txt({
    layout: true,
    text: value,
    fontFamily: stage.theme.font,
    fontSize: style.size,
    fontWeight: style.weight ?? 400,
    fill: style.color ?? stage.theme.text,
    lineHeight: style.size * 1.18,
    letterSpacing: style.spacing ?? 0,
    width: style.width,
    textWrap: true,
    textAlign: style.align ?? 'center',
  });
}

/** Shrink text blocks (already in the scene) to the widest one's natural width, at most `max`, so a short list or
 *  label hugs its content instead of sitting in an oversized box. Returns the width used. */
export function hug(nodes: Txt[], max: number): number {
  const natural = Math.max(...nodes.map(node => {
    node.width(DEFAULT); // auto: the text's natural, unwrapped width
    return node.width();
  }));
  const width = Math.min(Math.ceil(natural) + 1, max);
  nodes.forEach(node => node.width(width));
  return width;
}

/** Stack nodes top to bottom around `centerY`, with the given gaps between them. */
export function stack(nodes: {height(): number; y(v: number): unknown}[], gaps: number[], centerY = 0): void {
  const total = nodes.reduce((sum, node) => sum + node.height(), 0) + gaps.slice(0, nodes.length - 1).reduce((a, b) => a + b, 0);
  let top = centerY - total / 2;
  nodes.forEach((node, i) => {
    node.y(top + node.height() / 2);
    top += node.height() + (gaps[i] ?? 0);
  });
}
