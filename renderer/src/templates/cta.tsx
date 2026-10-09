/** @jsxImportSource @revideo/2d/lib */
import {Layout, Rect, Txt, type View2D} from '@revideo/2d';
import type {SceneSpec} from '../spec';
import {currentTheme} from '../themes/default';
import {playFor} from './common';

export function* cta(view: View2D, scene: SceneSpec) {
  const theme = currentTheme();
  const w = view.width();
  const portrait = view.height() > w;
  const node = (
    <Layout layout direction="column" alignItems="center" gap={48} width={w * 0.8}>
      <Txt text={scene.text.headline!} fontFamily={theme.font} fontWeight={800} fontSize={w * (portrait ? 0.065 : 0.045)}
        fill={theme.text} textWrap textAlign="center" width={w * 0.8} />
      {scene.text.subline ? (
        <Rect radius={999} fill={theme.accent} paddingLeft={56} paddingRight={56} paddingTop={24} paddingBottom={24}>
          <Txt text={scene.text.subline} fontFamily={theme.font} fontWeight={700} fontSize={w * (portrait ? 0.032 : 0.02)}
            fill={theme.background} textWrap textAlign="center" width={w * 0.65} />
        </Rect>
      ) : null}
      {scene.text.url ? (
        <Txt text={scene.text.url} fontFamily={theme.font} fontSize={w * (portrait ? 0.026 : 0.015)}
          fill={theme.muted} opacity={0.8} textAlign="center" />
      ) : null}
    </Layout>
  );
  yield* playFor(view, node, scene.duration);
}
