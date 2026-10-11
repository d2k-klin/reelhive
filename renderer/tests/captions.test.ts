import {describe, expect, it} from 'vitest';
import {phrases} from '../src/components/captions';
import type {SceneSpec} from '../src/spec';

const scene = (start: number, words: string[]): SceneSpec => ({
  index: 1, template: 'hook', start, duration: 5, narration: words.join(' '), text: {headline: 'x'},
  words: words.map((text, i) => ({text, start: 0.3 + i * 0.4, end: 0.3 + i * 0.4 + 0.35})),
});

describe('caption phrases', () => {
  it('break after punctuation and at four words, on the scene clock', () => {
    const result = phrases([scene(10, ['Cloud', 'bills', 'grow.', 'Most', 'teams', 'find', 'out', 'late'])]);
    expect(result.map(p => p.words.map(w => w.text).join(' '))).toEqual(['Cloud bills grow.', 'Most teams find out', 'late']);
    expect(result[0].start).toBeCloseTo(10.3);
  });

  it('give way to the next phrase and linger after the last', () => {
    const [first, second] = phrases([scene(0, ['One.', 'Two.'])]);
    expect(first.end).toBeCloseTo(second.start);
    expect(second.end).toBeCloseTo(0.3 + 0.4 + 0.35 + 0.4);
  });

  it('keep long words from overflowing a phrase', () => {
    const result = phrases([scene(0, ['Extraordinarily', 'comprehensive', 'observability'])]);
    expect(result.every(p => p.words.map(w => w.text).join(' ').length <= 28 || p.words.length === 1)).toBe(true);
  });
});
