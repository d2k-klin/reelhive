import type {Brief} from '../api/client';

/** Resolve the website fallback at request boundaries, keeping the saved draft's override optional. */
export function withScreenshotDefaults(brief: Partial<Brief>): Partial<Brief> {
  const visuals = brief.visuals;
  if (!['auto', 'screenshots'].includes(visuals?.source || 'auto')) return brief;
  const url = visuals?.screenshots?.url || visuals?.url || brief.website;
  if (!url) return brief;
  return {...brief, visuals: {source: 'auto', generate: false, ...visuals, url: null, screenshots: {
    routes: [], mask: [], frame: 'browser', ...visuals?.screenshots, url,
  }}};
}
