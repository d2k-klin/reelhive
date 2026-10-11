/** @jsxImportSource @revideo/2d/lib */
// Word-by-word captions: the narration shown in short phrases in the band below the content, each word lighting
// up in the accent colour as it is spoken. Times come from the recorded voice (scene.words, set in Python), so the
// captions stay on the voice to the frame. Runs alongside the shots for the whole video.
import {Rect, Txt, type Node} from '@revideo/2d';
import {all, easeOutCubic, type ThreadGenerator, waitFor} from '@revideo/core';
import type {SceneSpec} from '../spec';
import type {Stage} from '../stage';

const MAX_WORDS = 4;
const MAX_CHARS = 28;
const LINGER = 0.4; // a phrase stays this long after its last word, unless the next one starts sooner

interface Phrase {
  words: {text: string; start: number; end: number}[];
  start: number;
  end: number;
}

/** Short phrases that read at a glance: break after punctuation, or at four words / 28 characters. */
export function phrases(scenes: SceneSpec[]): Phrase[] {
  const result: Phrase[] = [];
  for (const scene of scenes) {
    let current: Phrase['words'] = [];
    const flush = () => {
      if (current.length) result.push({words: current, start: current[0].start, end: current[current.length - 1].end});
      current = [];
    };
    for (const word of scene.words ?? []) {
      const timed = {text: word.text, start: scene.start + word.start, end: scene.start + word.end};
      const length = [...current, timed].map(w => w.text).join(' ').length;
      if (current.length >= MAX_WORDS || (current.length && length > MAX_CHARS)) flush();
      current.push(timed);
      if (/[.,!?;:]$/.test(word.text)) flush();
    }
    flush();
  }
  // Each phrase gives way to the next one.
  result.forEach((phrase, i) => {
    const next = result[i + 1];
    phrase.end = Math.min(phrase.end + LINGER, next ? next.start : Infinity);
  });
  return result;
}

/** Adds the caption band to `layer` and returns its timeline (run with `yield`, not `yield*`). */
export function captionTrack(stage: Stage, layer: Node, scenes: SceneSpec[]): ThreadGenerator {
  const band = stage.captions!;
  const size = stage.s * 0.048;
  const pill = new Rect({
    layout: true, y: band.cy, opacity: 0, radius: size * 0.5, fill: stage.theme.background + 'cc',
    paddingLeft: size * 0.7, paddingRight: size * 0.7, paddingTop: size * 0.3, paddingBottom: size * 0.3, gap: size * 0.28,
  });
  layer.add(pill);
  return (function* () {
    let clock = 0;
    for (const phrase of phrases(scenes)) {
      yield* waitFor(Math.max(0, phrase.start - clock));
      pill.removeChildren();
      const words = phrase.words.map(w => new Txt({
        text: w.text, fontFamily: stage.theme.font, fontSize: size, fontWeight: 700, fill: stage.theme.text,
      }));
      words.forEach(word => pill.add(word));
      pill.scale(0.94);
      yield* all(pill.opacity(1, 0.12, easeOutCubic), pill.scale(1, 0.12, easeOutCubic));
      clock = phrase.start + 0.12;
      for (const [i, word] of phrase.words.entries()) {
        yield* waitFor(Math.max(0, word.start - clock));
        words.forEach((node, j) => node.fill(j === i ? stage.theme.accent : stage.theme.text));
        clock = Math.max(clock, word.start);
      }
      yield* waitFor(Math.max(0, phrase.end - clock - 0.1));
      yield* pill.opacity(0, 0.1);
      clock = Math.max(clock, phrase.end);
    }
  })();
}

/** The caption band as the layout report sees it: reserved space no shot may enter. */
export function captionBand(stage: Stage): Rect {
  const band = stage.captions!;
  return new Rect({layout: true, width: stage.content.w, height: band.h * 0.8, y: band.cy});
}
