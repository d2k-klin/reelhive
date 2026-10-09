// React 19 sets props on custom elements as properties when the element has that property. Revideo's
// <revideo-player> (0.11) defines `variables` as getter-only, so every preview update threw
// "Cannot set property variables ... which has only a getter" and blanked the page. Give it a setter
// that writes the attribute the element already observes (attributeChangedCallback -> setVariables).
// The element is registered lazily by @revideo/player-react, so patch it as soon as it is defined.
export function patchRevideoPlayer(Element: CustomElementConstructor) {
  const descriptor = Object.getOwnPropertyDescriptor(Element.prototype, 'variables');
  if (descriptor?.get && !descriptor.set) {
    Object.defineProperty(Element.prototype, 'variables', {
      ...descriptor,
      set(this: HTMLElement, value: unknown) {
        this.setAttribute('variables', typeof value === 'string' ? value : JSON.stringify(value));
      },
    });
  }
}

if (typeof customElements !== 'undefined') {
  void customElements.whenDefined('revideo-player').then(patchRevideoPlayer);
}
