import {Layout, Rect, Txt, type View2D} from '@revideo/2d';
import type {SceneSpec} from '../spec';
import {theme} from '../themes/default';
import {playFor} from './common';

export function* cta(view: View2D, scene: SceneSpec) {
  const w = view.width();
  const node = (
    <Layout layout direction="column" alignItems="center" gap={48} width={w * 0.8}>
      <Txt text={scene.text.headline!} fontFamily={theme.font} fontWeight={800} fontSize={w * 0.045}
        fill={theme.text} textWrap textAlign="center" width={w * 0.8} />
      {scene.text.subline ? (
        <Rect radius={999} fill={theme.accent} paddingLeft={56} paddingRight={56} paddingTop={24} paddingBottom={24}>
          <Txt text={scene.text.subline} fontFamily={theme.font} fontWeight={700} fontSize={w * 0.02}
            fill={theme.background} />
        </Rect>
      ) : null}
    </Layout>
  );
  yield* playFor(view, node, scene.duration);
}
