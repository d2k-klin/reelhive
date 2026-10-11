// What every template builds: a Shot. The orchestrator (scenes/from-spec.tsx) owns time: it runs the
// transition from the previous shot, the entrance, the layout report and the hold, in that order.
import {type Layout, Node, Rect} from '@revideo/2d';
import type {ThreadGenerator} from '@revideo/core';
import type {Device} from '../components/device';
import type {Part} from '../measure';
import {reveal} from '../motion';
import type {Stage} from '../stage';

export type Builder<T> = (stage: Stage, layer: Node, item: T) => Generator<any, Shot>;

export interface Shot {
  /** Everything in the shot, at the frame's centre; transitions move and fade this. */
  root: Node;
  /** Elements in reading order: what enters, and what the layout report measures. */
  parts: Part[];
  /** The product device, carried into the next shot when that one shows the product too. */
  device?: Device;
  /** The shot shows the logo itself, so the corner logo steps aside. */
  featuresLogo?: boolean;
  /** The entrance, exactly `seconds` long; `except` is a part another motion already brings in (a carried device). */
  enter(seconds: number, except?: Layout): ThreadGenerator;
  /** What happens once settled, exactly `seconds` long (a camera move, or stillness). */
  hold(seconds: number): ThreadGenerator;
}

/** The default entrance: parts rise into place in reading order. */
export function staggered(stage: Stage, parts: Part[]) {
  return (seconds: number, except?: Layout) =>
    reveal(parts.map(p => p.mover ?? p.node).filter(node => node !== except), seconds, stage.s * 0.03);
}

/** A shot root added to the stage, invisible until its transition starts. */
export function shotRoot(layer: Node): Node {
  const root = new Node({opacity: 0});
  layer.add(root);
  return root;
}

/** The short accent bar that marks a statement. */
export function accentBar(stage: Stage, color = stage.theme.accent): Rect {
  return new Rect({layout: true, width: stage.s * 0.11, height: stage.s * 0.01, radius: stage.s * 0.005, fill: color});
}
