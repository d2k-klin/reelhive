/** @jsxImportSource @revideo/2d/lib */
// The product on screen: a browser window, a phone or a plain card, with depth (shadow, layering) and a camera
// inside it. The camera establishes the whole screen first, then closes in on the planner's focus region, pans
// a tall page gently, or pushes in slowly; it never enlarges source pixels past MAX_SHARPNESS.
// A clip (the user's own video) plays muted from the moment its shot starts, and holds its last frame.
import {Circle, Img, Rect, Video} from '@revideo/2d';
import {all, delay, easeInOutSine, easeOutCubic, type ThreadGenerator, Vector2, waitFor} from '@revideo/core';
import type {Part} from '../measure';
import {exactly, glide} from '../motion';
import type {Visual} from '../spec';
import type {Stage} from '../stage';

/** Drawn pixels per source pixel the camera may reach; beyond this a screenshot visibly softens. */
export const MAX_SHARPNESS = 1.3;

export interface Device {
  frame: Rect;
  part: Part;
  /** Drawn pixels per source pixel at the closest framing, for the layout report. */
  zoom: number;
  /** The camera move while the shot holds; takes exactly `seconds`. */
  hold(seconds: number): ThreadGenerator;
}

export function* device(stage: Stage, visual: Visual, maxWidth: number, maxHeight: number): Generator<any, Device> {
  const {s, theme} = stage;
  const clip = visual.media === 'video';
  const image = clip
    ? new Video({src: visual.file, layout: false, volume: 0, decoder: 'web'})
    : new Img({src: visual.file, layout: false});
  yield image.toPromise();
  // A clip's size comes from the spec (measured when it was normalized), so layout never waits on decoding.
  const natural = clip ? new Vector2(visual.width!, visual.height!) : (image as Img).naturalSize();
  if (clip) (image as Video).play();
  const screenshot = visual.source === 'screenshot';
  const kind = visual.frame;
  const pad = kind === 'browser' ? s * 0.01 : kind === 'phone' ? s * 0.016 : 0;
  const bar = kind === 'browser' ? s * 0.038 : 0;
  const radius = kind === 'phone' ? s * 0.05 : s * 0.016;
  // Screenshots keep the capture viewport's shape (and scroll inside it); other images keep their own.
  const aspect = screenshot ? (kind === 'phone' ? 9 / 19.5 : stage.w / stage.h) : natural.x / natural.y;
  const screenWidth = Math.min(maxWidth - 2 * pad, (maxHeight - 2 * pad - bar) * aspect);
  const screenHeight = screenWidth / aspect;
  const frameWidth = screenWidth + 2 * pad, frameHeight = screenHeight + 2 * pad + bar;

  const frame = new Rect({
    width: frameWidth, height: frameHeight, radius, layout: false,
    fill: kind === 'phone' ? '#0b0c0f' : theme.surface,
    shadowColor: 'rgba(0,0,0,0.45)', shadowBlur: s * 0.06, shadowOffsetY: s * 0.024,
  });
  const screen = new Rect({
    width: screenWidth, height: screenHeight, y: bar / 2, clip: true, fill: '#ffffff',
    radius: kind === 'phone' ? radius - pad : kind === 'browser' ? s * 0.006 : radius,
  });
  frame.add(screen);
  if (kind === 'browser') {
    const y = -frameHeight / 2 + pad + bar / 2;
    ['#ff5f57', '#febc2e', '#28c840'].forEach((fill, i) =>
      frame.add(<Circle size={bar * 0.32} fill={fill} x={-frameWidth / 2 + pad + bar * (0.6 + i * 0.55)} y={y} />),
    );
    frame.add(<Rect width={screenWidth * 0.36} height={bar * 0.5} radius={999} fill={theme.background} opacity={0.6} y={y} />);
  }
  if (kind === 'phone') frame.add(<Rect width={screenWidth * 0.3} height={s * 0.014} radius={999} fill="#000" y={-screenHeight / 2 + s * 0.022} />);

  // Fit: a screenshot fills the width and starts at the top of the page; anything else fills the screen.
  const base = screenshot ? screenWidth / natural.x : Math.max(screenWidth / natural.x, screenHeight / natural.y);
  const size = natural.scale(base);
  image.size(size);
  image.y(screenshot ? (size.y - screenHeight) / 2 : 0);
  screen.add(image);
  const ceiling = Math.max(1, MAX_SHARPNESS / base);

  const focus = visual.focus;
  let closest = 1;
  let move: (seconds: number) => ThreadGenerator;
  if (focus) {
    // Where the region's centre sits on the image (image-local, origin at its centre) and how far to close in.
    const centre = new Vector2((focus.x + focus.width / 2 - 0.5) * size.x, (focus.y + focus.height / 2 - 0.5) * size.y);
    closest = Math.min(Math.max(1, 0.82 * Math.min(screenWidth / (focus.width * size.x), screenHeight / (focus.height * size.y))), ceiling);
    const limit = new Vector2(Math.max(0, (size.x * closest - screenWidth) / 2), Math.max(0, (size.y * closest - screenHeight) / 2));
    const target = new Vector2(
      Math.min(Math.max(-centre.x * closest, -limit.x), limit.x),
      Math.min(Math.max(-centre.y * closest, -limit.y), limit.y),
    );
    const ring = new Rect({
      x: centre.x, y: centre.y, width: focus.width * size.x * 1.08, height: focus.height * size.y * 1.08,
      radius: (s * 0.01) / closest, stroke: theme.accent, lineWidth: (s * 0.005) / closest, opacity: 0,
    });
    image.add(ring);
    move = function* (seconds) {
      const establish = Math.min(0.9, seconds * 0.3), travel = Math.min(1.4, seconds * 0.45);
      yield* exactly(seconds, delay(establish, all(
        image.scale(closest, travel, glide),
        image.position(target, travel, glide),
        delay(travel * 0.8, ring.opacity(1, 0.4, easeOutCubic)),
      )));
    };
  } else if (screenshot && size.y > screenHeight) {
    const travel = Math.min(size.y - screenHeight, screenHeight * 0.6);
    move = seconds => image.y(image.y() - travel, seconds, glide);
  } else {
    closest = Math.min(1.06, ceiling);
    move = seconds => image.scale(closest, seconds, easeInOutSine);
  }
  return {
    frame,
    part: {node: frame, role: 'visual'},
    zoom: base * closest,
    hold: seconds => (seconds > 0 ? move(seconds) : waitFor(0)),
  };
}
