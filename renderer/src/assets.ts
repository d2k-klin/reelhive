import {existsSync, readFileSync, realpathSync} from 'node:fs';
import {basename, dirname, isAbsolute, relative, resolve} from 'node:path';
import type {Spec} from './spec';

/** The one folder of a run the render server may serve: the normalized clips (src/reelhive/visuals/clips.py).
 *  Video is decoded by streaming it with range requests, which a data URL can't answer. */
export const CLIPS = 'visuals/clips';

/** The run's clip folder when it has one; render.ts makes it Vite's public folder and nothing else. */
export function clipsFolder(runDir: string): string | null {
  const folder = resolve(realpathSync(runDir), CLIPS);
  return existsSync(folder) ? realpathSync(folder) : null;
}

/** Embed run-local images so Vite never serves arbitrary filesystem paths; point clips at the clip folder. */
export function embedAssets(spec: Spec, runDir: string): Spec {
  const root = realpathSync(runDir);
  const inside = (name: string): string => {
    const path = realpathSync(resolve(root, name));
    const rel = relative(root, path);
    if (rel.startsWith('..') || isAbsolute(rel)) throw new Error('image must be inside the run folder');
    return path;
  };
  const dataUrl = (name: string): string => {
    const path = inside(name);
    const ext = path.split('.').pop()?.toLowerCase();
    const mime = {png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', webp: 'image/webp'}[ext ?? ''];
    if (!mime) throw new Error(`unsupported image: ${name}`);
    return `data:${mime};base64,${readFileSync(path).toString('base64')}`;
  };
  const clipUrl = (name: string): string => {
    const path = inside(name);
    if (dirname(path) !== resolve(root, CLIPS) || !path.toLowerCase().endsWith('.mp4')) {
      throw new Error(`clips must be normalized MP4 files in ${CLIPS}: ${name}`);
    }
    return `/${encodeURIComponent(basename(path))}`;
  };
  return {...spec,
    theme: {...spec.theme, ...(spec.theme?.logo ? {logo: dataUrl(spec.theme.logo)} : {})},
    scenes: spec.scenes.map(scene => ({...scene,
      visual: scene.visual
        ? {...scene.visual, file: scene.visual.media === 'video' ? clipUrl(scene.visual.file) : dataUrl(scene.visual.file)}
        : null,
    })),
  };
}
