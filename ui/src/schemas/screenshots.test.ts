import {expect, it} from 'vitest';
import type {Brief} from '../api/client';
import {withScreenshotDefaults} from './screenshots';

const brief = {website: 'https://product.example', visuals: {source: 'auto', generate: false}} as Brief;

it('uses the product website without mutating the draft or freezing future website changes', () => {
  expect(withScreenshotDefaults(brief).visuals?.screenshots?.url).toBe(brief.website);
  expect(brief.visuals?.screenshots).toBeUndefined();
  expect(withScreenshotDefaults({...brief, website: 'https://new.example'}).visuals?.screenshots?.url).toBe('https://new.example');
});

it('keeps routes, masks, framing and sign-in state when inheriting the website', () => {
  const options = {url: '', routes: ['/dashboard'], mask: ['.email'], frame: 'phone' as const, storage_state: '/tmp/auth.json'};
  expect(withScreenshotDefaults({...brief, visuals: {source: 'screenshots', generate: false, screenshots: options}}).visuals?.screenshots)
    .toEqual({...options, url: brief.website});
});

it('preserves explicit screenshot URLs and the URL shortcut', () => {
  const screenshots = {url: 'https://app.example', frame: 'none' as const};
  expect(withScreenshotDefaults({...brief, visuals: {source: 'auto', generate: false, screenshots}}).visuals?.screenshots?.url).toBe(screenshots.url);
  expect(withScreenshotDefaults({...brief, visuals: {source: 'auto', generate: false, url: screenshots.url}}).visuals?.screenshots?.url).toBe(screenshots.url);
});

it('adds no captures without a website or when another visual source is selected', () => {
  const noWebsite = {...brief, website: null};
  expect(withScreenshotDefaults(noWebsite)).toBe(noWebsite);
  for (const source of ['none', 'images', 'generate'] as const) {
    const other = {...brief, visuals: {source, generate: false}};
    expect(withScreenshotDefaults(other)).toBe(other);
  }
});
