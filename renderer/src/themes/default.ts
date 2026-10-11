import {useScene} from '@revideo/core';

export const theme = {
  background: '#0f1115',
  surface: '#1a1d24',
  text: '#f5f5f4',
  muted: '#a8a29e',
  accent: '#f5a524',
  // Bundled with the renderer (@fontsource-variable/inter, loaded in project.ts), so every machine draws the same type.
  font: '"Inter Variable", Inter, Helvetica Neue, Helvetica, Arial, sans-serif',
};

export type Theme = typeof theme & {logo?: string | null};

export function currentTheme(): Theme {
  const spec = useScene().variables.get('spec', {theme: {}})() as {theme?: Partial<Theme>};
  return {...theme, ...spec.theme};
}
