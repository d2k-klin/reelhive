/** @jsxImportSource @revideo/2d/lib */
// The product reveal after the hook: logo, the name, one line on what it is, and the address, small.
import type {Layout} from '@revideo/2d';
import {waitFor} from '@revideo/core';
import type {Part} from '../measure';
import type {Intro} from '../spec';
import {stack, text} from '../stage';
import {logoMark} from './closing';
import {accentBar, type Builder, shotRoot, staggered} from './kit';

export const intro: Builder<Intro> = function* (stage, layer, item) {
  const {theme, type, s, measure} = stage;
  const root = shotRoot(layer);
  const nodes: Layout[] = [];
  const parts: Part[] = [];
  const logo = yield* logoMark(stage, s * 0.12);
  if (logo) {
    nodes.push(logo);
    parts.push({node: logo, role: 'logo'});
  } else {
    const bar = accentBar(stage);
    nodes.push(bar);
    parts.push({node: bar, role: null});
  }
  // Names are short; long ones shrink so they stay on one or two lines.
  const fit = Math.min(1, 16 / Math.max(item.title.length, 1));
  const title = text(stage, item.title, {size: type.display * fit, weight: 800, width: measure, spacing: -type.display * fit * 0.02});
  nodes.push(title);
  parts.push({node: title, role: 'title'});
  if (item.tagline) {
    const tagline = text(stage, item.tagline, {size: type.body * 1.15, color: theme.muted, width: measure * 0.8});
    nodes.push(tagline);
    parts.push({node: tagline, role: 'tagline'});
  }
  if (item.url) {
    const url = text(stage, item.url, {size: type.url, color: theme.muted, width: measure});
    nodes.push(url);
    parts.push({node: url, role: 'url'});
  }
  nodes.forEach(node => root.add(node));
  stack(nodes, nodes.map((_, i) => s * (i === 0 ? 0.05 : 0.03)));
  return {root, parts, featuresLogo: !!logo, enter: staggered(stage, parts), hold: waitFor};
};
