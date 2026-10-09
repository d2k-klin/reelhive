// @vitest-environment jsdom
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import type {Brief} from './api/client';
import {DRAFT_KEY, reuseBrief} from './draft';

const brief = {level: 'medium', audience: 'Developers', storyline: 'A story', features: ['One'], closing: 'Try it', duration: 45} as Brief;

beforeEach(() => localStorage.clear());
afterEach(() => vi.restoreAllMocks());

describe('reuseBrief', () => {
  it('fills the brief form with the earlier brief so a new run can be created from it', () => {
    expect(reuseBrief(brief)).toBe(true);
    expect(JSON.parse(localStorage.getItem(DRAFT_KEY) || 'null')).toEqual(brief);
  });

  it('does nothing without a brief', () => {
    expect(reuseBrief(null)).toBe(false);
    expect(localStorage.getItem(DRAFT_KEY)).toBeNull();
  });

  it('asks before replacing an unsaved draft and keeps it when declined', () => {
    localStorage.setItem(DRAFT_KEY, '{"audience":"Mine"}');
    const ask = vi.spyOn(window, 'confirm').mockReturnValueOnce(false).mockReturnValueOnce(true);
    expect(reuseBrief(brief)).toBe(false);
    expect(localStorage.getItem(DRAFT_KEY)).toBe('{"audience":"Mine"}');
    expect(reuseBrief(brief)).toBe(true);
    expect(JSON.parse(localStorage.getItem(DRAFT_KEY) || 'null')).toEqual(brief);
    expect(ask).toHaveBeenCalledTimes(2);
  });
});
