import {describe, expect, it} from 'vitest';
import {SuggestionsSchema} from './suggestions';

const ok = {label: 'Punchier hook', instruction: 'Open with the cost number, keep the rest.'};

describe('propose_suggestions arguments', () => {
  it('accepts 3-4 bounded suggestions', () => {
    expect(SuggestionsSchema.safeParse({suggestions: [ok, ok, ok]}).success).toBe(true);
    expect(SuggestionsSchema.safeParse({suggestions: [ok, ok, ok, ok]}).success).toBe(true);
  });

  it('rejects malformed tool output so nothing renders or applies', () => {
    for (const bad of [
      {suggestions: [ok, ok]},                                              // too few
      {suggestions: [ok, ok, ok, ok, ok]},                                  // too many
      {suggestions: [{...ok, label: 'x'.repeat(29)}, ok, ok]},             // label too long
      {suggestions: [{...ok, instruction: 'short'}, ok, ok]},              // no real instruction
      {suggestions: [{label: 'Hi'}, ok, ok]},                              // missing field
      {items: [ok, ok, ok]},                                                // wrong shape
    ]) {
      expect(SuggestionsSchema.safeParse(bad).success).toBe(false);
    }
  });
});
