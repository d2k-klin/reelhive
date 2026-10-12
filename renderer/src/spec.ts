// The render contract. spec.schema.json is generated from the Pydantic models in
// src/reelhive/schemas/scene_spec.py; a pytest contract test keeps the two in sync.
import schema from './spec.schema.json';

export type Template = 'hook' | 'feature-card' | 'cta' | 'image-full' | 'screenshot-pan' | 'problem' | 'stat' | 'bullets';

export interface Focus {
  x: number;
  y: number;
  width: number;
  height: number;
  label: string;
}

export interface Visual {
  source: 'provided' | 'screenshot' | 'generated';
  file: string;
  /** `video`: the user's own clip, played muted from its first frame; its last frame holds after it ends. */
  media?: 'image' | 'video';
  frame: 'browser' | 'phone' | 'none';
  focus?: Focus | null;
  /** Video only: seconds of clip, and its pixel size (measured in Python when the clip is normalized). */
  duration?: number | null;
  width?: number | null;
  height?: number | null;
}

export type ShotLayout = 'center' | 'split-left' | 'split-right';

export interface SceneSpec {
  index: number;
  template: Template;
  start: number;
  duration: number;
  narration: string;
  hold?: number;
  layout?: ShotLayout;
  /** The narration's words as spoken, in seconds from the scene's start. */
  words?: {text: string; start: number; end: number}[];
  visual?: Visual | null;
  text: Record<string, any>;
}

export interface Motion {
  enter: number;
  transition: number;
}

export interface Credit {
  mode: 'end' | 'corner';
  text: string;
  duration: number;
}

export interface Intro {
  title: string;
  tagline?: string | null;
  url?: string | null;
  duration: number;
}

export interface Spec {
  version: number;
  theme?: Record<string, string | null>;
  width: number;
  height: number;
  fps: number;
  duration: number;
  motion?: Motion;
  captions?: boolean;
  intro?: Intro | null;
  intro_at?: number;
  scenes: SceneSpec[];
  credit: Credit | null;
}

const TEXT_DEFS: Record<Template, string> = {
  hook: 'HookText',
  'feature-card': 'FeatureCardText',
  cta: 'CtaText',
  'image-full': 'HookText',
  'screenshot-pan': 'HookText',
  problem: 'HookText', stat: 'StatText', bullets: 'BulletsText',
};

/** Character limits per field of one text definition, read from the generated JSON Schema. */
function limitsOf(def: string): Record<string, number> {
  const props = (schema as any).$defs[def].properties as Record<string, any>;
  const limits: Record<string, number> = {};
  for (const [field, prop] of Object.entries(props)) {
    const max = prop.maxLength ?? prop.anyOf?.find((d: any) => d.maxLength)?.maxLength;
    if (max) limits[field] = max;
  }
  return limits;
}

/** Character limits per template field. */
export function limitsFor(template: Template): Record<string, number> {
  return limitsOf(TEXT_DEFS[template]);
}

/** Throws on an intro that would overflow; Python validates first, this is the last guard. */
export function checkIntro(intro: Intro): Intro {
  for (const [field, max] of Object.entries(limitsOf('Intro'))) {
    const value = (intro as any)[field];
    if (typeof value === 'string' && value.length > max) {
      throw new Error(`intro: ${field} is ${value.length} chars, limit ${max}`);
    }
  }
  return intro;
}

/** Throws on text that would overflow a template; Python validates first, this is the last guard. */
export function checkScene(scene: SceneSpec): SceneSpec {
  if (!(scene.template in TEXT_DEFS)) throw new Error(`scene ${scene.index}: unknown template ${scene.template}`);
  for (const [field, max] of Object.entries(limitsFor(scene.template))) {
    const value = scene.text[field];
    if (value && value.length > max) {
      throw new Error(`scene ${scene.index}: ${field} is ${value.length} chars, limit ${max}`);
    }
  }
  if (scene.template === 'bullets' && (!Array.isArray(scene.text.items) || scene.text.items.length > 5 || scene.text.items.some((item: string) => item.length > 70))) {
    throw new Error(`scene ${scene.index}: bullets exceed template limits`);
  }
  return scene;
}
