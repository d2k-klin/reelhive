/** @jsxImportSource @revideo/2d/lib */
// Typographic shots: one statement, a number, or a short list. Big type, an accent mark, generous space.
import {Circle, Layout, type Node, type Txt} from '@revideo/2d';
import {all, easeOutCubic, tween, waitFor} from '@revideo/core';
import type {Part} from '../measure';
import {reveal} from '../motion';
import type {SceneSpec} from '../spec';
import {hug, type Stage, stack, text} from '../stage';
import {accentBar, type Builder, type Shot, shotRoot, staggered} from './kit';

function* statement(stage: Stage, layer: Node, scene: SceneSpec, mark: string): Generator<any, Shot> {
  const {theme, type, measure} = stage;
  const root = shotRoot(layer);
  const bar = accentBar(stage, mark);
  const headline = text(stage, scene.text.headline, {size: type.hero, weight: 800, width: measure});
  const nodes: Layout[] = [bar, headline];
  const parts: Part[] = [{node: bar, role: null}, {node: headline, role: 'headline'}];
  if (scene.text.subline) {
    const subline = text(stage, scene.text.subline, {size: type.body, color: theme.muted, width: measure * 0.8});
    nodes.push(subline);
    parts.push({node: subline, role: 'subline'});
  }
  nodes.forEach(node => root.add(node));
  stack(nodes, [stage.s * 0.045, stage.s * 0.035]);
  return {root, parts, enter: staggered(stage, parts), hold: waitFor};
}

export const hook: Builder<SceneSpec> = (stage, layer, scene) => statement(stage, layer, scene, stage.theme.accent);

/** The pain before the product: the same statement shape, with a muted mark. */
export const problem: Builder<SceneSpec> = (stage, layer, scene) =>
  statement(stage, layer, {...scene, text: {...scene.text, subline: scene.text.subline ?? 'There is a better way.'}}, stage.theme.muted);

/** "40%" counts up from 0 to 40 as it arrives; text without a leading number simply arrives. */
function countUp(node: Txt, value: string, seconds: number) {
  const match = /^(\D*?)(\d[\d,]*(?:\.\d+)?)(.*)$/.exec(value);
  if (!match) return waitFor(seconds);
  const [, before, number, after] = match;
  const target = Number(number.replace(/,/g, ''));
  const decimals = number.includes('.') ? number.split('.')[1].length : 0;
  const grouped = number.includes(',');
  const format = (v: number) => {
    const fixed = v.toFixed(decimals);
    return grouped ? Number(fixed).toLocaleString('en-US', {minimumFractionDigits: decimals}) : fixed;
  };
  return tween(seconds, t => node.text(before + format(target * easeOutCubic(t)) + after), () => node.text(value));
}

export const stat: Builder<SceneSpec> = function* (stage, layer, scene) {
  const {theme, type, measure} = stage;
  const root = shotRoot(layer);
  const figure = text(stage, scene.text.headline, {size: type.display, weight: 800, color: theme.accent, width: measure});
  const nodes: Layout[] = [figure];
  const parts: Part[] = [{node: figure, role: 'headline'}];
  if (scene.text.subline) {
    const subline = text(stage, scene.text.subline, {size: type.body * 1.15, width: measure * 0.8});
    nodes.push(subline);
    parts.push({node: subline, role: 'subline'});
  }
  nodes.forEach(node => root.add(node));
  stack(nodes, [stage.s * 0.03]);
  return {
    root, parts, hold: waitFor,
    enter: seconds => all(staggered(stage, parts)(seconds), countUp(figure, scene.text.headline, seconds)),
  };
};

export const bullets: Builder<SceneSpec> = function* (stage, layer, scene) {
  const {theme, type, s} = stage;
  const root = shotRoot(layer);
  const max = Math.min(stage.content.w, s * 1.2);
  const dot = s * 0.014, gap = s * 0.025;
  const headline = text(stage, scene.text.headline, {size: type.headline, weight: 800, width: max, align: 'left'});
  const labels = (scene.text.items as string[]).map(item =>
    text(stage, item, {size: type.body, color: theme.muted, width: max - dot - gap, align: 'left'}),
  );
  const rows = labels.map(label => {
    const row = new Layout({layout: true, direction: 'row', gap, alignItems: 'center'});
    row.add(<Circle size={dot} fill={theme.accent} />);
    row.add(label);
    return row;
  });
  [headline, ...rows].forEach(node => root.add(node));
  // The block is as wide as its longest line, and centred as a block; lines stay left-aligned inside it.
  const width = Math.max(hug([headline], max), hug(labels, max - dot - gap) + dot + gap);
  headline.width(width);
  stack([headline, ...rows], [s * 0.05, ...rows.map(() => s * 0.024)]);
  rows.forEach(row => row.x(-width / 2 + row.width() / 2));
  const parts: Part[] = [{node: headline, role: 'headline'}, ...labels.map((label, i) => ({node: label, role: 'item' as const, mover: rows[i]}))];
  return {root, parts, enter: (seconds, except) => reveal([headline, ...rows].filter(n => n !== except), seconds, s * 0.03), hold: waitFor};
};
