/** @jsxImportSource @revideo/2d/lib */
import {Layout, Rect, Txt, type View2D} from '@revideo/2d';
import type {Intro} from '../spec';
import {currentTheme} from '../themes/default';
import {playFor} from './common';

/** The title screen before the first scene: the name, one line on what it is, and the address, small. */
export function* introCard(view: View2D, intro: Intro) {
  const theme = currentTheme();
  const w = view.width();
  const portrait = view.height() > w;
  // Names are short; shrink long ones so they stay on one or two lines.
  const fit = Math.min(1, 16 / Math.max(intro.title.length, 1));
  const node = (
    <Layout layout direction="column" alignItems="center" gap={44} width={w * 0.84}>
      <Rect width={160} height={12} radius={6} fill={theme.accent} />
      <Txt text={intro.title} fontFamily={theme.font} fontWeight={800} fontSize={w * (portrait ? 0.13 : 0.085) * fit}
        fill={theme.text} textWrap textAlign="center" width={w * 0.84} />
      {intro.tagline ? (
        <Txt text={intro.tagline} fontFamily={theme.font} fontSize={w * (portrait ? 0.045 : 0.026)}
          fill={theme.muted} textWrap textAlign="center" width={w * 0.7} />
      ) : null}
      {intro.url ? (
        <Txt text={intro.url} fontFamily={theme.font} fontSize={w * (portrait ? 0.028 : 0.016)}
          fill={theme.muted} opacity={0.8} textAlign="center" />
      ) : null}
    </Layout>
  );
  yield* playFor(view, node, intro.duration);
}
