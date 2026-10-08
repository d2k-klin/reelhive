/** @jsxImportSource @revideo/2d/lib */
import {Layout, Rect, Txt, type View2D} from '@revideo/2d';
import type {SceneSpec} from '../spec';
import {currentTheme} from '../themes/default';
import {playFor} from './common';

export function* hook(view: View2D, scene: SceneSpec) {
  const theme = currentTheme();
  const w = view.width();
  const portrait = view.height() > w;
  const node = (
    <Layout layout direction="column" alignItems="center" gap={36} width={w * 0.8}>
      <Rect width={120} height={10} radius={5} fill={theme.accent} />
      <Txt text={scene.text.headline!} fontFamily={theme.font} fontWeight={800} fontSize={w * (portrait ? 0.075 : 0.05)}
        fill={theme.text} textWrap textAlign="center" width={w * 0.8} />
      {scene.text.subline ? (
        <Txt text={scene.text.subline} fontFamily={theme.font} fontSize={w * (portrait ? 0.036 : 0.022)}
          fill={theme.muted} textWrap textAlign="center" width={w * 0.7} />
      ) : null}
    </Layout>
  );
  yield* playFor(view, node, scene.duration);
}
