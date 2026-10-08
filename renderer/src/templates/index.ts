import type {Template} from '../spec';
import {cta} from './cta';
import {featureCard} from './feature-card';
import {hook} from './hook';

export const TEMPLATES: Record<Template, typeof hook> = {hook, 'feature-card': featureCard, cta};
