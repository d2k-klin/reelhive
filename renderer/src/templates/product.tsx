/** @jsxImportSource @revideo/2d/lib */
// The product: a device with its headline. `center` shows the full view with the text below; `split-left` and
// `split-right` put the device on one side and the explanation on the other (stacked on portrait formats, where
// two columns would be too narrow to read).
import type {Layout} from '@revideo/2d';
import {device} from '../components/device';
import type {Part} from '../measure';
import type {SceneSpec} from '../spec';
import {stack, text} from '../stage';
import {type Builder, shotRoot, staggered} from './kit';

export const product: Builder<SceneSpec> = function* (stage, layer, scene) {
  if (!scene.visual) throw new Error(`scene ${scene.index}: image is missing`);
  const {theme, type, s, content, portrait} = stage;
  const root = shotRoot(layer);
  const layout = scene.layout ?? 'center';
  const side = !portrait && layout !== 'center';
  const align = side || (portrait && layout !== 'center') ? 'left' : 'center';
  const textWidth = side ? content.w * 0.36 : Math.min(content.w, stage.measure);
  const supporting = scene.text.subline || scene.text.body;

  const headline = text(stage, scene.text.headline, {size: type.headline, weight: 800, width: textWidth, align});
  const copy: Layout[] = [headline];
  const parts: Part[] = [];
  let subline: Layout | undefined;
  if (supporting) {
    subline = text(stage, supporting, {size: type.body, color: theme.muted, width: textWidth, align});
    copy.push(subline);
  }
  copy.forEach(node => root.add(node));
  stack(copy, [s * 0.025]);
  const copyHeight = copy.reduce((sum, node) => sum + node.height(), 0) + (subline ? s * 0.025 : 0);

  const maxWidth = side ? content.w * 0.58 : content.w * (portrait ? 1 : 0.8);
  const maxHeight = side ? content.h * 0.86 : content.h - copyHeight - s * 0.06;
  const shown = yield* device(stage, scene.visual, maxWidth, maxHeight);
  root.add(shown.frame);

  if (side) {
    // Each sits in the middle of its own column: 58% of the width for the device, 36% for the text.
    const deviceX = content.left + content.w * 0.29;
    const textX = content.left + content.w - textWidth / 2;
    const [visualX, copyX] = layout === 'split-left' ? [deviceX, textX] : [-deviceX, -textX];
    shown.frame.x(visualX);
    copy.forEach(node => node.x(copyX));
    parts.push(shown.part, {node: headline, role: 'headline'});
  } else {
    // Device above, copy below, the pair centred in the content box.
    const gap = s * 0.05;
    const total = shown.frame.height() + gap + copyHeight;
    shown.frame.y(-total / 2 + shown.frame.height() / 2);
    const offset = -total / 2 + shown.frame.height() + gap + copyHeight / 2;
    copy.forEach(node => node.y(node.y() + offset));
    parts.push(shown.part, {node: headline, role: 'headline'});
  }
  if (subline) parts.push({node: subline, role: 'subline'});
  return {root, parts, device: shown, enter: staggered(stage, parts), hold: shown.hold};
};
