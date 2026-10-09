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
  it('supports remount sizing, frame rate, quality and optional prop removal', () => {
    class Sized extends HTMLElement {}
    for (const name of ['width', 'height', 'fps', 'quality']) {
      Object.defineProperty(Sized.prototype, name, {configurable:true, get() {return this.getAttribute(name);}});
    }
    customElements.define('sized-revideo-player', Sized);
    patchRevideoPlayer(Sized);
    patchRevideoPlayer(Sized); // registration and subsequent mounts can safely reuse the shim
    const element = document.createElement('sized-revideo-player') as any;
    for (const [name, value] of Object.entries({width:640,height:360,fps:30,quality:1})) {
      element[name] = value;
      expect(element.getAttribute(name)).toBe(String(value));
      element[name] = undefined;
      expect(element.hasAttribute(name)).toBe(false);
    }
  });
});
