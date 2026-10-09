// Usage: tsx render.ts <spec.json> <out.mp4>
// Prints `progress <0..1>` lines that src/reelhive/render/bridge.py parses.
import {renderVideo} from '@revideo/renderer';
import {readFileSync} from 'node:fs';
import {basename, dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {embedAssets} from './src/assets';
import {installBrowserShutdownGuard} from './src/browser-shutdown';
import type {Spec} from './src/spec';

process.env.DISABLE_TELEMETRY = 'true';

const [specPath, outPath] = process.argv.slice(2);
if (!specPath || !outPath || !outPath.endsWith('.mp4')) {
  console.error('usage: tsx render.ts <spec.json> <out.mp4>');
  process.exit(2);
}
const spec: Spec = embedAssets(JSON.parse(readFileSync(specPath, 'utf8')), dirname(resolve(specPath)));
const here = dirname(fileURLToPath(import.meta.url));

// Revideo owns browser creation and closure; guard its launch in this isolated render process.
installBrowserShutdownGuard();

await renderVideo({
  projectFile: resolve(here, 'src/project.ts'),
  variables: {spec},
  settings: {
    outDir: dirname(resolve(outPath)),
    outFile: basename(outPath) as `${string}.mp4`,
    logProgress: false,
    // Revideo forces --single-process, which full Chrome rejects on macOS; headless-shell accepts it.
    puppeteer: {headless: 'shell'},
    progressCallback: (_worker, progress) => console.log(`progress ${progress.toFixed(3)}`),
    projectSettings: {
      size: {x: spec.width, y: spec.height},
      exporter: {name: '@revideo/core/ffmpeg', options: {format: 'mp4'}},
    },
  },
});
console.log('done');
