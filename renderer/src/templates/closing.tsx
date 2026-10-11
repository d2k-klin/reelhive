/** @jsxImportSource @revideo/2d/lib */
// The closing: the logo, a finished call to action, a pill and the address. It arrives and then stays: the last
// frame settles instead of fading out, and the credit (if any) appears beneath it.
import {Img, Rect, type Layout} from '@revideo/2d';
import {waitFor} from '@revideo/core';
import type {Part} from '../measure';
import type {SceneSpec} from '../spec';
import {hug, type Stage, stack, text} from '../stage';
import {type Builder, shotRoot, staggered} from './kit';

/** The brand mark at a size that sits above a title. */
export function* logoMark(stage: Stage, height: number): Generator<any, Img | null> {
  if (!stage.theme.logo) return null;
  const logo = new Img({src: stage.theme.logo, layout: true});
  yield logo.toPromise();
  const natural = logo.naturalSize();
  logo.size(natural.scale(Math.min(height / natural.y, (stage.s * 0.5) / natural.x)));
  return logo;
}

export const closing: Builder<SceneSpec> = function* (stage, layer, scene) {
  const {theme, type, s, measure} = stage;
  const root = shotRoot(layer);
  const nodes: Layout[] = [];
  const parts: Part[] = [];
  const logo = yield* logoMark(stage, s * 0.1);
  if (logo) {
    nodes.push(logo);
    parts.push({node: logo, role: 'logo'});
  }
  const headline = text(stage, scene.text.headline, {size: type.hero, weight: 800, width: measure});
  nodes.push(headline);
  parts.push({node: headline, role: 'headline'});
  if (scene.text.subline) {
    const label = text(stage, scene.text.subline, {size: type.body, weight: 700, color: theme.background, width: measure * 0.6});
    const pill = new Rect({layout: true, radius: 999, fill: theme.accent, paddingLeft: s * 0.05, paddingRight: s * 0.05, paddingTop: s * 0.022, paddingBottom: s * 0.022});
    pill.add(label);
    root.add(pill);
    hug([label], measure * 0.6);
    nodes.push(pill);
    parts.push({node: label, role: 'subline', mover: pill});
  }
  if (scene.text.url) {
    const url = text(stage, scene.text.url, {size: type.url, color: theme.muted, width: measure});
    nodes.push(url);
    parts.push({node: url, role: 'url'});
  }
  nodes.forEach(node => root.add(node));
  stack(nodes, nodes.map(() => s * 0.045));
  return {root, parts, featuresLogo: !!logo, enter: staggered(stage, parts), hold: waitFor};
};
