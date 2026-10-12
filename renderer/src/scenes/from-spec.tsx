/** @jsxImportSource @revideo/2d/lib */
// Walks the spec as one continuous piece. For every shot, in playing order (the intro sits at `intro_at`):
//   transition from the previous shot ─ entrance (staggered, exactly motion.enter) ─ layout report ─ hold
// The layout report also records when each shot cuts in, lands and closes in, read off the clock that drives it.
// so each shot lasts exactly its duration and the voice, timed in Python, lands on its scene.
//
// Transitions are one grammar for the whole video, chosen from what meets at each cut:
//   carry   product → product: the device travels to its new place while the screen changes (shared element)
//   settle  into the intro or the closing: the old shot eases forward and away, the new one settles into place
//   push    anything else: the old shot drifts out, the new one comes in from the same direction
import {makeScene2D, Img, Node, type View2D} from '@revideo/2d';
import {all, delay, easeOutCubic, useScene, useThread, type ThreadGenerator, waitFor} from '@revideo/core';
import {backdrop} from '../components/backdrop';
import {captionBand, captionTrack} from '../components/captions';
import {type Moment, report} from '../measure';
import {easeInCubic, glide, spring} from '../motion';
import {checkIntro, checkScene, type Intro, type SceneSpec, type Spec} from '../spec';
import {type Stage, stageOf} from '../stage';
import {addCreditCorner, creditEnd} from '../templates/credit';
import {TEMPLATES} from '../templates';
import {intro as introShot} from '../templates/intro';
import type {Shot} from '../templates/kit';
import {currentTheme, type Theme} from '../themes/default';

/** Share of a cut in which the outgoing shot clears; the incoming entrance starts as it does, so the two
 *  compositions never sit on top of each other at full strength. */
const CLEAR = 0.5;

type Item = {kind: 'intro'; intro: Intro} | {kind: 'scene'; scene: SceneSpec};

function timeline(spec: Spec): Item[] {
  const items: Item[] = spec.scenes.map(scene => ({kind: 'scene', scene}));
  if (spec.intro) items.splice(spec.intro_at ?? 0, 0, {kind: 'intro', intro: spec.intro});
  return items;
}

function* fontsReady(theme: Theme) {
  // Text is measured for layout, so the bundled face must be ready before the first shot is built.
  yield Promise.all([400, 700, 800].map(weight => document.fonts.load(`${weight} 64px ${theme.font}`)));
}

function* cornerLogo(stage: Stage, layer: Node): Generator<any, Img | null> {
  if (!stage.theme.logo) return null;
  const logo = new Img({src: stage.theme.logo, opacity: 0});
  yield logo.toPromise();
  const natural = logo.naturalSize();
  logo.size(natural.scale(Math.min((stage.w * 0.09) / natural.x, (stage.h * 0.07) / natural.y)));
  logo.position([stage.w / 2 - stage.w * 0.06 - logo.width() / 2, -stage.h / 2 + stage.h * 0.06 + logo.height() / 2]);
  layer.add(logo);
  return logo;
}

function* transition(stage: Stage, prev: Shot | null, next: Shot, seconds: number, settle: boolean): ThreadGenerator {
  next.root.opacity(1);
  if (!prev) return;
  const motions: ThreadGenerator[] = [];
  if (prev.device && next.device) {
    const a = prev.device.frame, b = next.device.frame;
    const target = b.position(), from = a.position();
    const ratio = a.width() / b.width();
    b.position(from);
    b.scale(ratio);
    b.opacity(0);
    motions.push(
      b.position(target, seconds, glide), b.scale(1, seconds, glide), b.opacity(1, seconds * 0.6, easeOutCubic),
      a.position(target, seconds, glide), a.scale(1 / ratio, seconds, glide), a.opacity(0, seconds, easeInCubic),
      ...prev.parts.filter(p => p.node !== a).map(p => (p.mover ?? p.node).opacity(0, seconds * CLEAR, easeOutCubic)),
    );
  } else if (settle) {
    next.root.scale(0.96);
    motions.push(
      prev.root.scale(1.04, seconds, easeInCubic), prev.root.opacity(0, seconds * CLEAR, easeOutCubic),
      next.root.scale(1, seconds, spring),
    );
  } else {
    const distance = stage.s * 0.08;
    const axis = stage.portrait ? 'y' : 'x';
    next.root[axis](distance);
    motions.push(
      prev.root[axis](-distance, seconds, easeInCubic), prev.root.opacity(0, seconds * CLEAR, easeOutCubic),
      next.root[axis](0, seconds, spring),
    );
  }
  yield* all(...motions);
  prev.root.remove();
}

export default makeScene2D('from-spec', function* (view: View2D) {
  const spec = useScene().variables.get('spec', null as unknown as Spec)();
  const theme = currentTheme();
  yield* fontsReady(theme);
  const captions = !!spec.captions && spec.scenes.some(scene => scene.words?.length);
  const stage = stageOf(view, theme, captions);
  // Shots are laid out around the content centre, which moves up when the caption band takes the bottom.
  const back = new Node({}), shots = new Node({y: stage.content.cy}), front = new Node({});
  view.add(back);
  view.add(shots);
  view.add(front);
  yield backdrop(stage, back); // runs for the whole video alongside the shots
  const corner = yield* cornerLogo(stage, front);
  if (spec.credit?.mode === 'corner') addCreditCorner(view);
  const band = captions ? captionBand(stage) : null;
  if (band) {
    front.add(band);
    yield captionTrack(stage, front, spec.scenes); // follows the voice for the whole video
  }

  const motion = {enter: 0.8, transition: 0.6, ...spec.motion};
  const items = timeline(spec);
  let prev: Shot | null = null;
  for (const [position, item] of items.entries()) {
    const duration = item.kind === 'intro' ? checkIntro(item.intro).duration : checkScene(item.scene).duration;
    const shot: Shot = item.kind === 'intro'
      ? yield* introShot(stage, shots, item.intro)
      : yield* TEMPLATES[item.scene.visual ? 'image-full' : item.scene.template](stage, shots, item.scene);
    const enter = Math.min(motion.enter, duration * 0.5);
    const cut = Math.min(motion.transition, enter);
    const carried = !!(prev?.device && shot.device);
    const settle = item.kind === 'intro' || position === items.length - 1;
    const lead = prev ? cut * CLEAR * 0.8 : 0;
    const startsAt = useThread().time();
    const moments: Moment[] = [
      {kind: 'cut', at: startsAt, detail: !prev ? 'open' : carried ? 'carry' : settle ? 'settle' : 'push'},
    ];
    yield* all(
      transition(stage, prev, shot, cut, settle),
      delay(lead, shot.enter(enter - lead, carried ? shot.device!.frame : undefined)),
      corner ? corner.opacity(shot.featuresLogo ? 0 : 0.75, cut) : waitFor(0),
    );
    const measured = band ? [...shot.parts, {node: band, role: 'caption' as const}] : shot.parts;
    const settledAt = useThread().time(), holding = Math.max(0, duration - enter);
    moments.push({kind: 'arrive', at: settledAt, detail: item.kind === 'intro' ? 'intro' : item.scene.template});
    const landing = shot.device?.landing(holding);
    if (landing != null && item.kind === 'scene') {
      moments.push({kind: 'focus', at: settledAt + landing, detail: item.scene.visual?.focus?.label || 'region'});
    }
    report(view, item.kind, item.kind === 'intro' ? 0 : item.scene.index, measured, shot.device?.zoom ?? 1, moments);
    yield* shot.hold(holding);
    prev = shot;
  }
  // The closing frame stays; the end credit appears beneath it.
  if (spec.credit?.mode === 'end') yield* creditEnd(view, spec.credit);
});
