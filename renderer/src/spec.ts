// The render contract. spec.schema.json is generated from the Pydantic models in
// src/reelhive/schemas/scene_spec.py; a pytest contract test keeps the two in sync.
import schema from './spec.schema.json';

export type Template = 'hook' | 'feature-card' | 'cta' | 'image-full' | 'screenshot-pan';

export interface SceneSpec {
  index: number;
  template: Template;
  start: number;
  duration: number;
  narration: string;
  visual?: {source: 'provided' | 'screenshot' | 'generated'; file: string; frame: 'browser' | 'phone' | 'none'} | null;
  text: Record<string, string | null | undefined>;
}

export interface Credit {
  mode: 'end' | 'corner';
  text: string;
  duration: number;
}

export interface Spec {
  version: number;
  theme?: Record<string, string | null>;
  width: number;
  height: number;
  fps: number;
  duration: number;
  scenes: SceneSpec[];
  credit: Credit | null;
}

const TEXT_DEFS: Record<Template, string> = {
  hook: 'HookText',
  'feature-card': 'FeatureCardText',
  cta: 'CtaText',
  'image-full': 'HookText',
  'screenshot-pan': 'HookText',
};

/** Character limits per template field, read from the generated JSON Schema. */
export function limitsFor(template: Template): Record<string, number> {
  const props = (schema as any).$defs[TEXT_DEFS[template]].properties as Record<string, any>;
  const limits: Record<string, number> = {};
  for (const [field, def] of Object.entries(props)) {
    const max = def.maxLength ?? def.anyOf?.find((d: any) => d.maxLength)?.maxLength;
    if (max) limits[field] = max;
  }
  return limits;
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
  return scene;
}
