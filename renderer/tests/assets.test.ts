import {afterEach, describe, expect, it} from 'vitest';
import {mkdtempSync, writeFileSync, rmSync, mkdirSync, symlinkSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {clipsFolder, embedAssets} from '../src/assets';
import type {Spec} from '../src/spec';

const roots: string[] = [];
afterEach(() => roots.splice(0).forEach(root => rmSync(root, {recursive: true, force: true})));
const make = () => {const root = mkdtempSync(join(tmpdir(), 'reelhive-')); roots.push(root); return root;};
const spec = (file: string): Spec => ({version: 1, width: 1080, height: 1920, fps: 30, duration: 2, credit: null,
  theme: {logo: file}, scenes: [{index: 1, template: 'image-full', start: 0, duration: 2, narration: '',
    text: {headline: 'Hello'}, visual: {file, source: 'provided', frame: 'none'}}]});

describe('local images', () => {
  it('embeds images and logos without changing the saved spec', () => {
    const root = make(); writeFileSync(join(root, 'asset.png'), 'pixels');
    const original = spec('asset.png'); const result = embedAssets(original, root);
    expect(result.scenes[0].visual?.file).toBe('data:image/png;base64,cGl4ZWxz');
    expect(result.theme?.logo).toBe(result.scenes[0].visual?.file);
    expect(original.scenes[0].visual?.file).toBe('asset.png');
  });
  it('rejects traversal and symlinks outside the run folder', () => {
    const root = make(); mkdirSync(join(root, 'run')); writeFileSync(join(root, 'secret.png'), 'secret');
    symlinkSync(join(root, 'secret.png'), join(root, 'run', 'link.png'));
    for (const file of ['../secret.png', 'link.png']) {
      expect(() => embedAssets(spec(file), join(root, 'run'))).toThrow(/inside the run/);
    }
  });
});

describe('local clips', () => {
  const video = (file: string): Spec => ({...spec('asset.png'), theme: {}, scenes: [{...spec('asset.png').scenes[0],
    visual: {file, source: 'provided', frame: 'none', media: 'video', duration: 2, width: 1920, height: 1080}}]});
  it('points clips at the clip folder, the only folder the render server may serve', () => {
    const root = make(); mkdirSync(join(root, 'visuals', 'clips'), {recursive: true});
    writeFileSync(join(root, 'visuals', 'clips', 'scene_01.mp4'), 'frames');
    expect(embedAssets(video('visuals/clips/scene_01.mp4'), root).scenes[0].visual?.file).toBe('/scene_01.mp4');
    expect(clipsFolder(root)).toMatch(/visuals\/clips$/);
  });
  it('rejects a clip anywhere else in the run, and runs without clips serve nothing', () => {
    const root = make(); writeFileSync(join(root, 'raw.mp4'), 'frames');
    expect(() => embedAssets(video('raw.mp4'), root)).toThrow(/normalized MP4/);
    expect(clipsFolder(root)).toBeNull();
  });
});
