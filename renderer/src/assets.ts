import {readFileSync, realpathSync} from 'node:fs';
import {isAbsolute, relative, resolve} from 'node:path';
import type {Spec} from './spec';

/** Embed run-local images so Vite never serves arbitrary filesystem paths. */
export function embedAssets(spec: Spec, runDir: string): Spec {
  const root = realpathSync(runDir);
  const dataUrl = (name: string): string => {
    const path = realpathSync(resolve(root, name));
    const rel = relative(root, path);
    if (rel.startsWith('..') || isAbsolute(rel)) throw new Error('image must be inside the run folder');
    const ext = path.split('.').pop()?.toLowerCase();
    const mime = {png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', webp: 'image/webp'}[ext ?? ''];
    if (!mime) throw new Error(`unsupported image: ${name}`);
    return `data:${mime};base64,${readFileSync(path).toString('base64')}`;
  };
  return {...spec,
    theme: {...spec.theme, ...(spec.theme?.logo ? {logo: dataUrl(spec.theme.logo)} : {})},
    scenes: spec.scenes.map(scene => ({...scene,
      visual: scene.visual ? {...scene.visual, file: dataUrl(scene.visual.file)} : null,
    })),
  };
}
