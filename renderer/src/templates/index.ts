import type {SceneSpec, Template} from '../spec';
import {closing} from './closing';
import {offer, review} from './commerce';
import {featureCard} from './feature-card';
import type {Builder} from './kit';
import {photo} from './photo';
import {product} from './product';
import {bullets, hook, problem, stat} from './statements';

export const TEMPLATES: Record<Template, Builder<SceneSpec>> = {
  hook, problem, stat, bullets, offer, review, photo, cta: closing,
  'feature-card': featureCard,
  'image-full': product,
  'screenshot-pan': product,
};
