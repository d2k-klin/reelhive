import type {SceneSpec, Template} from '../spec';
import {closing} from './closing';
import {featureCard} from './feature-card';
import type {Builder} from './kit';
import {product} from './product';
import {bullets, hook, problem, stat} from './statements';

export const TEMPLATES: Record<Template, Builder<SceneSpec>> = {
  hook, problem, stat, bullets, cta: closing,
  'feature-card': featureCard,
  'image-full': product,
  'screenshot-pan': product,
};
