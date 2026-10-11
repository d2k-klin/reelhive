// The layout report: once a shot has settled, measure where its elements really are in the frame and print one
// line that src/reelhive/render/bridge.py collects into render/layout.json for the `review` node's gates.
// The shape is src/reelhive/schemas/layout.py (ShotLayout); Python validates every line it reads.
import {Txt, type Layout, type View2D} from '@revideo/2d';

export const LAYOUT_MARKER = 'REELHIVE_LAYOUT ';

export type Role = 'headline' | 'subline' | 'body' | 'label' | 'item' | 'url' | 'title' | 'tagline' | 'caption' | 'visual' | 'logo';

export interface Part {
  node: Layout;
  /** What the element is; null for decoration that the gates ignore (accent bars, dots). */
  role: Role | null;
  /** What enters and leaves, when it is a container around the measured element (a pill around its text). */
  mover?: Layout;
}

function box(part: Part & {role: Role}) {
  const position = part.node.absolutePosition();
  const scale = part.node.absoluteScale();
  const width = part.node.width() * Math.abs(scale.x);
  const height = part.node.height() * Math.abs(scale.y);
  const isText = part.node instanceof Txt;
  return {
    role: part.role,
    // absolutePosition is in canvas pixels from the frame's top-left corner.
    x: position.x - width / 2,
    y: position.y - height / 2,
    width,
    height,
    font_size: isText ? (part.node as Txt).fontSize() * Math.abs(scale.y) : null,
    text: isText ? (part.node as Txt).text() : null,
  };
}

export function report(view: View2D, kind: 'intro' | 'scene', index: number, parts: Part[], zoom = 1): void {
  const boxes = parts.filter((p): p is Part & {role: Role} => p.role !== null).map(box);
  console.log(LAYOUT_MARKER + JSON.stringify({kind, index, width: view.width(), height: view.height(), boxes, zoom}));
}
