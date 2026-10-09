// @vitest-environment jsdom
import {describe, expect, it} from 'vitest';
import {patchRevideoPlayer} from './revideo-player-fix';

describe('revideo-player React 19 shim', () => {
  it('turns a getter-only `variables` into an attribute write', () => {
    class Fake extends HTMLElement {
      get variables() { return JSON.parse(this.getAttribute('variables') || '{}'); }
    }
    customElements.define('fake-revideo-player', Fake);
    patchRevideoPlayer(Fake);
    const element = document.createElement('fake-revideo-player') as Fake & {variables: unknown};
    element.variables = {spec: {duration: 3}};
    expect(element.getAttribute('variables')).toBe('{"spec":{"duration":3}}');
    expect(element.variables).toEqual({spec: {duration: 3}});
  });
});
