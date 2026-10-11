/** @jsxImportSource @revideo/2d/lib */
// One feature, one card: a large accent marker, the headline and a line of detail on a raised surface.
import {Rect, Txt} from '@revideo/2d';
import {all, delay, easeOutCubic, waitFor} from '@revideo/core';
import type {Part} from '../measure';
import {exactly, spring} from '../motion';
import type {SceneSpec} from '../spec';
import {text} from '../stage';
import {type Builder, shotRoot} from './kit';

export const featureCard: Builder<SceneSpec> = function* (stage, layer, scene) {
  const {theme, type, s, portrait} = stage;
  const root = shotRoot(layer);
  const width = Math.min(stage.content.w, s * (portrait ? 0.86 : 1.35));
  const column = portrait ? width - s * 0.1 : width * 0.68;
  const card = new Rect({
    layout: true, direction: portrait ? 'column' : 'row', alignItems: portrait ? 'start' : 'center',
    gap: s * (portrait ? 0.03 : 0.06), padding: s * 0.05, radius: s * 0.035, width,
    fill: theme.surface, stroke: theme.accent + '66', lineWidth: s * 0.002,
    shadowColor: 'rgba(0,0,0,0.4)', shadowBlur: s * 0.05, shadowOffsetY: s * 0.02,
  });
  const marker = new Txt({
    text: scene.text.label ?? String(scene.index).padStart(2, '0'), fontFamily: theme.font,
    fontSize: type.display * 0.75, fontWeight: 800, fill: theme.accent,
  });
  const copy = new Rect({layout: true, direction: 'column', gap: s * 0.02, width: column});
  const headline = text(stage, scene.text.headline, {size: type.headline, weight: 800, width: column, align: 'left'});
  copy.add(headline);
  const parts: Part[] = [{node: marker, role: 'label', mover: card}, {node: headline, role: 'headline'}];
  if (scene.text.body) {
    const body = text(stage, scene.text.body, {size: type.body, color: theme.muted, width: column, align: 'left'});
    copy.add(body);
    parts.push({node: body, role: 'body'});
  }
  card.add(marker);
  card.add(copy);
  root.add(card);
  const inner = parts.map(p => p.node);
  return {
    root, parts, hold: waitFor,
    enter: seconds => {
      // The card rises into place, then its contents arrive in reading order.
      card.opacity(0);
      card.y(card.y() + s * 0.04);
      inner.forEach(node => node.opacity(0));
      const step = Math.min(0.12, seconds / 6);
      return exactly(seconds, all(
        card.opacity(1, seconds * 0.5, easeOutCubic),
        card.y(card.y() - s * 0.04, seconds * 0.7, spring),
        ...inner.map((node, i) => delay(seconds * 0.25 + i * step, node.opacity(1, seconds * 0.4, easeOutCubic))),
      ));
    },
  };
};
