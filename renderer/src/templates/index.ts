import {stat, bullets, problem} from './extras';
import {imageFull} from './image-full';
import type {Template} from '../spec';
import {cta} from './cta';
import {featureCard} from './feature-card';
import {hook} from './hook';

export const TEMPLATES: Record<Template, typeof hook> = {hook, 'feature-card': featureCard, cta, 'image-full': imageFull, 'screenshot-pan': imageFull, problem, stat, bullets};
