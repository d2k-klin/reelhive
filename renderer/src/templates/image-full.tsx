/** @jsxImportSource @revideo/2d/lib */
import {Img, Layout, Rect, Txt, type View2D} from '@revideo/2d';
import {all, createRef} from '@revideo/core';
import type {SceneSpec} from '../spec';
import {currentTheme} from '../themes/default';
import {playFor} from './common';

export function* imageFull(view: View2D, scene: SceneSpec) {
  if (!scene.visual) throw new Error(`scene ${scene.index}: image is missing`);
  const theme = currentTheme();
  const w = view.width(), h = view.height();
  const portrait = h > w;
  const frame = scene.visual.frame;
  const imageWidth = w * (frame === 'phone' && !portrait ? 0.3 : 0.84);
  const imageHeight = h * 0.56;
  const screenshot = scene.visual.source === 'screenshot';
  const picture = createRef<Img>();
  const node = (
    <Layout layout direction="column" alignItems="center" gap={h * 0.035}>
      <Rect layout direction="column" fill={theme.surface} radius={frame === 'phone' ? 40 : 18}
        padding={frame === 'none' ? 0 : 16}>
        {frame === 'browser' ? <Txt text="●  ●  ●" fill={theme.muted} fontSize={18} height={36} /> : null}
        <Rect width={imageWidth} height={imageHeight} clip radius={frame === 'phone' ? 28 : 8}>
          <Img ref={picture} src={scene.visual.file} layout={false} />
        </Rect>
      </Rect>
      <Txt text={scene.text.headline!} fontFamily={theme.font} fontWeight={800}
        fontSize={w * (portrait ? 0.058 : 0.035)} width={w * 0.84} textWrap textAlign="center" fill={theme.text} />
      {(scene.text.subline || scene.text.body) ? <Txt text={scene.text.subline || scene.text.body || ''}
        fontFamily={theme.font} fontSize={w * (portrait ? 0.032 : 0.02)} width={w * 0.8}
        textWrap textAlign="center" fill={theme.muted} /> : null}
    </Layout>
  );
  yield picture().toPromise();
  const natural = picture().naturalSize();
  const scale = screenshot ? imageWidth / natural.x : Math.min(imageWidth / natural.x, imageHeight / natural.y);
  picture().size(natural.scale(scale));
  // The screenshot is clipped to the frame; travel from its top to its bottom.
  const travel = screenshot ? Math.max(0, picture().height() - imageHeight) / 2 : 0;
  picture().y(travel);
  yield* all(playFor(view, node, scene.duration), picture().y(-travel, scene.duration));
}
