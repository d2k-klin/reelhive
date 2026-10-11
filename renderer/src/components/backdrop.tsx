/** @jsxImportSource @revideo/2d/lib */
// A quiet background with depth: a diagonal gradient between the theme's background and surface, and two soft
// accent glows that drift very slowly for the whole video. It stays behind every shot and never competes.
import {Circle, Gradient, Rect, type Node} from '@revideo/2d';
import {all, chain, easeInOutSine, loop, type ThreadGenerator} from '@revideo/core';
import type {Stage} from '../stage';

function glow(stage: Stage, size: number, alpha: string, x: number, y: number): Circle {
  return new Circle({
    size, x, y,
    fill: new Gradient({
      type: 'radial', fromRadius: 0, toRadius: size / 2,
      stops: [{offset: 0, color: stage.theme.accent + alpha}, {offset: 1, color: stage.theme.accent + '00'}],
    }),
  });
}

/** Adds the backdrop to `layer` and returns its drift, to run alongside the shots (`yield`, not `yield*`). */
export function backdrop(stage: Stage, layer: Node): ThreadGenerator {
  const {w, h, s, theme} = stage;
  layer.add(
    <Rect width={w} height={h} fill={new Gradient({
      type: 'linear', from: [-w / 2, -h / 2], to: [w / 2, h / 2],
      stops: [{offset: 0, color: theme.background}, {offset: 1, color: theme.surface}],
    })} />,
  );
  const a = glow(stage, s * 1.1, '24', -w * 0.32, -h * 0.28);
  const b = glow(stage, s * 0.9, '14', w * 0.34, h * 0.3);
  layer.add(a);
  layer.add(b);
  return loop(() => chain(
    all(a.position([-w * 0.22, -h * 0.18], 9, easeInOutSine), b.position([w * 0.26, h * 0.2], 9, easeInOutSine)),
    all(a.position([-w * 0.32, -h * 0.28], 9, easeInOutSine), b.position([w * 0.34, h * 0.3], 9, easeInOutSine)),
  ));
}
