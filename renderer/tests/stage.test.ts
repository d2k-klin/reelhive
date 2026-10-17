import type {View2D} from '@revideo/2d';
import {describe, expect, it} from 'vitest';
import {stageOf} from '../src/stage';
import {theme} from '../src/themes/default';

const view = (w: number, h: number) => ({width: () => w, height: () => h}) as unknown as View2D;
const REELS = {top: 0.13, right: 0.12, bottom: 0.22, left: 0.05}; // PLATFORM_SAFE_AREAS["reels"]

describe('stage', () => {
  it('keeps the title-safe layout every template was designed on', () => {
    const {content, captions} = stageOf(view(1920, 1080), theme, true);
    const band = 1080 * 0.16;
    expect(content.w).toBeCloseTo(1920 * 0.86);
    expect(content.h).toBeCloseTo(1080 * 0.84 - band);
    expect(content.left).toBeCloseTo(-1920 * 0.43);
    expect(content.top).toBeCloseTo(-1080 * 0.42);
    expect(content.cy).toBeCloseTo(-band / 2);
    expect(captions!.cy).toBeCloseTo(1080 * 0.42 - band / 2);
  });

  it("lays a platform cut out clear of the app's buttons, captions band included", () => {
    const w = 1080, h = 1920;
    const {content, captions} = stageOf(view(w, h), theme, true, REELS);
    const box = {left: w / 2 + content.left, right: w / 2 + content.left + content.w};
    expect(box.left).toBeGreaterThan(w * REELS.left);
    expect(box.right).toBeLessThan(w * (1 - REELS.right));
    expect(box.left).toBeCloseTo(w - box.right); // still centred
    const top = h / 2 + content.cy - content.h / 2, bandBottom = h / 2 + captions!.cy + captions!.h / 2;
    expect(top).toBeGreaterThan(h * REELS.top);
    expect(bandBottom).toBeLessThan(h * (1 - REELS.bottom));
    expect(bandBottom).toBeCloseTo(top + content.h + captions!.h);
  });
});
