import {Layout, Rect, Txt, type View2D} from '@revideo/2d';
import type {SceneSpec} from '../spec';
import {currentTheme} from '../themes/default';
import {playFor} from './common';

export function* featureCard(view: View2D, scene: SceneSpec) {
  const theme = currentTheme();
  const w = view.width();
  const portrait = view.height() > w;
  const node = (
    <Rect layout direction={portrait ? "column" : "row"} alignItems="center" gap={portrait ? 36 : 64} padding={w * 0.04} radius={40}
      fill={theme.surface} width={w * 0.78} stroke={theme.accent} lineWidth={3}>
      <Txt text={scene.text.label ?? String(scene.index)} fontFamily={theme.font} fontWeight={800}
        fontSize={w * 0.07} fill={theme.accent} />
      <Layout layout direction="column" gap={24} grow={1}>
        <Txt text={scene.text.headline!} fontFamily={theme.font} fontWeight={700} fontSize={w * (portrait ? 0.055 : 0.034)}
          fill={theme.text} textWrap width={w * (portrait ? 0.66 : 0.5)} />
        {scene.text.body ? (
          <Txt text={scene.text.body} fontFamily={theme.font} fontSize={w * (portrait ? 0.035 : 0.019)}
            fill={theme.muted} textWrap width={w * (portrait ? 0.66 : 0.5)} />
        ) : null}
      </Layout>
    </Rect>
  );
  yield* playFor(view, node, scene.duration);
}
