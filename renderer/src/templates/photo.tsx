/** @jsxImportSource @revideo/2d/lib */
// A photo story's shot: one of the user's photos across the whole frame, under a slow camera move that runs for the
// whole shot (the Ken Burns effect), with an optional caption low in the frame over a soft shade. Photos dissolve
// into one another (scenes/from-spec.tsx); the caption arrives like every other shot's text.
import {Gradient, Img, Rect, type Txt} from '@revideo/2d';
import {all, createSignal, linear, type ThreadGenerator} from '@revideo/core';
import type {Part} from '../measure';
import {exactly, glide, reveal} from '../motion';
import type {SceneSpec} from '../spec';
import {stack, text} from '../stage';
import {type Builder, shotRoot} from './kit';

/** How far the camera travels: the photo grows (or shrinks) by this much, or pans with this much to spare. */
export const TRAVEL = 1.12;

export const photo: Builder<SceneSpec> = function* (stage, layer, scene) {
  const {type, s, w, h, content} = stage;
  const root = shotRoot(layer);
  const image = new Img({src: scene.visual!.file, layout: false});
  yield image.toPromise();
  const natural = image.naturalSize();
  const cover = Math.max(w / natural.x, h / natural.y); // fills the frame, cropping the longer side
  image.size(natural.scale(cover));
  // The shots layer sits at the content centre (it rises when captions take the bottom); the photo fills the frame.
  image.y(-content.cy);
  root.add(image);

  const motion = (scene as SceneSpec & {motion?: string}).motion ?? 'push_in';
  const progress = createSignal(0);
  const eased = () => glide(progress());
  if (motion === 'push_in' || motion === 'pull_out') {
    const [from, to] = motion === 'push_in' ? [1, TRAVEL] : [TRAVEL, 1];
    image.scale(() => from + (to - from) * eased());
  } else {
    // The photo is enlarged by TRAVEL so it can slide without showing an edge; pan_left looks further left as it goes.
    // ponytail: a gentle 8% of the frame each way, even when a wide photo in a tall frame has far more to spare.
    const travel = Math.min(((image.width() * TRAVEL - w) / 2) * 0.9, w * 0.08);
    const [from, to] = motion === 'pan_left' ? [-travel, travel] : [travel, -travel];
    image.scale(TRAVEL);
    image.x(() => from + (to - from) * eased());
  }

  const parts: Part[] = [];
  const nodes: Txt[] = [];
  if (scene.text.headline) {
    const shade = new Rect({
      layout: false, width: w, height: h * 0.5, y: h * 0.25 - content.cy,
      fill: new Gradient({type: 'linear', from: [0, -h * 0.25], to: [0, h * 0.25], stops: [
        {offset: 0, color: 'rgba(0,0,0,0)'}, {offset: 1, color: 'rgba(0,0,0,0.72)'},
      ]}),
    });
    root.add(shade);
    const headline = text(stage, scene.text.headline, {size: type.headline, weight: 800, width: stage.measure, color: '#ffffff'});
    nodes.push(headline);
    parts.push({node: headline, role: 'headline'});
    if (scene.text.subline) {
      const subline = text(stage, scene.text.subline, {size: type.body, width: stage.measure * 0.85, color: '#ffffffd9'});
      nodes.push(subline);
      parts.push({node: subline, role: 'subline'});
    }
    nodes.forEach(node => root.add(node));
    // Low in the frame, on the bottom of the content box (above the caption band and a platform's buttons).
    const height = nodes.reduce((sum, node) => sum + node.height(), 0) + (nodes.length - 1) * s * 0.02;
    stack(nodes, [s * 0.02], content.h / 2 - height / 2);
  }

  // The move spans the whole shot at one speed: its entrance, then its hold, as one glide.
  const total = Math.max(scene.duration, 0.001);
  const move = (seconds: number, to: number): ThreadGenerator => progress(to, seconds, linear);
  let elapsed = 0;
  return {
    root, parts, fullBleed: true,
    // Pixels of the photo drawn per source pixel at the closest framing (the review's sharpness gate).
    zoom: cover * TRAVEL,
    enter: seconds => {
      elapsed = seconds;
      return all(move(seconds, Math.min(1, seconds / total)), reveal(nodes, seconds, s * 0.02));
    },
    hold: seconds => exactly(seconds, move(seconds, Math.min(1, (elapsed + seconds) / total))),
  };
};
