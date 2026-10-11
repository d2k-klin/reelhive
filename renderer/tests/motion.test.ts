import {describe, expect, it} from 'vitest';
import {glide, spring} from '../src/motion';

describe('motion curves', () => {
  it('start at 0 and land exactly at 1, so every shot keeps its frame-exact length', () => {
    for (const curve of [spring, glide]) {
      expect(curve(0)).toBeCloseTo(0, 6);
      expect(curve(1)).toBeCloseTo(1, 6);
    }
  });

  it('spring overshoots a little and never wildly; glide never overshoots', () => {
    const samples = Array.from({length: 201}, (_, i) => i / 200);
    const peak = Math.max(...samples.map(spring));
    expect(peak).toBeGreaterThan(1.03);
    expect(peak).toBeLessThan(1.12);
    expect(Math.max(...samples.map(glide))).toBeLessThanOrEqual(1);
  });
});
