/** @jsxImportSource @revideo/2d/lib */
// Commerce shots: what it costs, and what customers say. Prices and quotes come from the sources (the critic's
// `claims` check holds them to the brief and the website's product data); these templates only set them well.
import {Layout, Line, Rect, type Txt} from '@revideo/2d';
import {all, delay, easeOutCubic, waitFor} from '@revideo/core';
import type {Part} from '../measure';
import {reveal} from '../motion';
import type {SceneSpec} from '../spec';
import {hug, type Stage, stack, text} from '../stage';
import {accentBar, type Builder, shotRoot, staggered} from './kit';

/** A five-pointed star of outer radius `r`, as the points of a closed line. */
function starPoints(r: number): [number, number][] {
  return Array.from({length: 10}, (_, i) => {
    const radius = i % 2 ? r * 0.45 : r;
    const angle = -Math.PI / 2 + (i * Math.PI) / 5;
    return [Math.cos(angle) * radius, Math.sin(angle) * radius] as [number, number];
  });
}

/** Five stars filled up to `rating`, half stars included. Drawn, not typed, so no font can lack the glyph. */
function stars(stage: Stage, rating: number): Rect {
  const size = stage.s * 0.05, gap = size * 0.22;
  const row = new Rect({width: 5 * size + 4 * gap, height: size});
  for (let i = 0; i < 5; i++) {
    const x = -row.width() / 2 + size / 2 + i * (size + gap);
    row.add(<Line points={starPoints(size / 2)} closed fill={stage.theme.surface} x={x} />);
    const filled = Math.max(0, Math.min(1, rating - i)) * size;
    if (!filled) continue;
    const clip = new Rect({clip: true, width: filled, height: size, x: x - size / 2 + filled / 2});
    clip.add(<Line points={starPoints(size / 2)} closed fill={stage.theme.accent} x={size / 2 - filled / 2} />);
    row.add(clip);
  }
  return row;
}

/** The price, big in the accent colour, after the earlier one struck through; the strike draws in as it lands. */
export const offer: Builder<SceneSpec> = function* (stage, layer, scene) {
  const {theme, type, measure, s} = stage;
  const root = shotRoot(layer);
  const headline = text(stage, scene.text.headline, {size: type.headline, weight: 700, width: measure});
  const price = text(stage, scene.text.price, {size: type.display, weight: 800, color: theme.accent, width: measure});
  const row = new Layout({layout: true, direction: 'row', gap: s * 0.04, alignItems: 'center'});
  let was: Txt | null = null, strike: Rect | null = null, wrap: Layout | null = null;
  if (scene.text.was) {
    was = text(stage, scene.text.was, {size: type.headline, weight: 600, color: theme.muted, width: measure});
    wrap = new Layout({layout: true});
    wrap.add(was);
    row.add(wrap);
  }
  row.add(price);
  const nodes: Layout[] = [headline, row];
  root.add(headline);
  root.add(row);
  hug([price], measure * 0.7);
  if (was && wrap) {
    hug([was], measure * 0.3);
    strike = new Rect({layout: false, width: was.width() * 1.08, height: s * 0.007, radius: s * 0.004, fill: theme.text, rotation: -8});
    wrap.add(strike);
  }
  const parts: Part[] = [{node: headline, role: 'headline'}];
  if (was) parts.push({node: was, role: 'label'});
  parts.push({node: price, role: 'headline'});
  if (scene.text.subline) {
    const subline = text(stage, scene.text.subline, {size: type.body, color: theme.muted, width: measure * 0.8});
    root.add(subline);
    nodes.push(subline);
    parts.push({node: subline, role: 'subline'});
  }
  stack(nodes, [s * 0.035, s * 0.03]);
  return {
    root, parts, hold: waitFor,
    enter: (seconds, except) => {
      strike?.scale.x(0);
      return all(
        // The row arrives as one, so the old price and the new one stay side by side.
        reveal(nodes.filter(n => n !== except), seconds, s * 0.03),
        strike ? delay(seconds * 0.6, strike.scale.x(1, seconds * 0.4, easeOutCubic)) : waitFor(0),
      );
    },
  };
};

/** A customer's words in quotation marks, under their stars (or an accent mark without a rating), and who said it. */
export const review: Builder<SceneSpec> = function* (stage, layer, scene) {
  const {theme, type, measure, s} = stage;
  const root = shotRoot(layer);
  const mark = scene.text.rating != null ? stars(stage, scene.text.rating) : accentBar(stage);
  const quote = text(stage, `“${scene.text.headline}”`, {size: type.headline, weight: 700, width: measure});
  const nodes: Layout[] = [mark, quote];
  const parts: Part[] = [{node: mark, role: null}, {node: quote, role: 'headline'}];
  if (scene.text.subline) {
    const author = text(stage, `— ${scene.text.subline}`, {size: type.body, color: theme.muted, width: measure * 0.8});
    nodes.push(author);
    parts.push({node: author, role: 'subline'});
  }
  nodes.forEach(node => root.add(node));
  stack(nodes, [s * 0.045, s * 0.035]);
  return {root, parts, enter: staggered(stage, parts), hold: waitFor};
};
