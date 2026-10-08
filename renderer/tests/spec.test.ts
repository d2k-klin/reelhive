import {describe, expect, it} from 'vitest';
import schema from '../src/spec.schema.json';
import {checkScene, limitsFor, type SceneSpec, type Template} from '../src/spec';
import {TEMPLATES} from '../src/templates';

const scene = (template: Template, text: Record<string, string>): SceneSpec => ({
  index: 1, template, start: 0, duration: 2, narration: 'x', text,
});

describe('render contract', () => {
  it('reads character limits from the generated schema', () => {
    expect(limitsFor('feature-card')).toEqual({label: 4, headline: 40, body: 110});
    expect(limitsFor('hook')).toEqual({headline: 48, subline: 80});
    expect(limitsFor('cta')).toEqual({headline: 60, subline: 60});
  });

  it('rejects text that would overflow a template', () => {
    expect(() => checkScene(scene('hook', {headline: 'x'.repeat(49)}))).toThrow(/headline is 49 chars, limit 48/);
    expect(checkScene(scene('hook', {headline: 'x'.repeat(48)})).template).toBe('hook');
  });

  it('rejects unknown templates', () => {
    expect(() => checkScene(scene('stat' as Template, {headline: 'x'}))).toThrow(/unknown template/);
  });

  it('has a component for every template in the schema', () => {
    const mapping = (schema as any).properties.scenes.items.discriminator.mapping as Record<string, string>;
    expect(Object.keys(TEMPLATES).sort()).toEqual(Object.keys(mapping).sort());
  });
});
