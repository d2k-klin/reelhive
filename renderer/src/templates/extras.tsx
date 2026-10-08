/** @jsxImportSource @revideo/2d/lib */
import {Layout, Rect, Txt, type View2D} from '@revideo/2d';
import type {SceneSpec} from '../spec';
import {currentTheme} from '../themes/default';
import {playFor} from './common';
import {hook} from './hook';

export function* problem(view: View2D, scene: SceneSpec) {
  yield* hook(view, {...scene, text: {...scene.text, subline: scene.text.subline ?? 'There is a better way.'}});
}
export function* stat(view: View2D, scene: SceneSpec) {
  const theme = currentTheme(), w = view.width();
  yield* playFor(view, <Layout layout direction="column" gap={40} alignItems="center" width={w * .8}>
    <Txt text={scene.text.headline} fontFamily={theme.font} fontWeight={800} fontSize={w * .12} fill={theme.accent} width={w * .8} textWrap textAlign="center" />
    <Txt text={scene.text.subline ?? ''} fontFamily={theme.font} fontSize={w * .035} fill={theme.text} width={w * .75} textWrap textAlign="center" />
  </Layout>, scene.duration);
}
export function* bullets(view: View2D, scene: SceneSpec) {
  const theme = currentTheme(), w = view.width();
  yield* playFor(view, <Layout layout direction="column" gap={32} width={w * .78}>
    <Txt text={scene.text.headline} fontFamily={theme.font} fontWeight={800} fontSize={w * .055} fill={theme.text} width={w * .78} textWrap />
    {(scene.text.items as string[]).map(item => <Layout layout direction="row" gap={24} alignItems="center">
      <Rect width={12} height={12} radius={6} fill={theme.accent} />
      <Txt text={item} fontFamily={theme.font} fontSize={w * .032} fill={theme.muted} width={w * .7} textWrap />
    </Layout>)}
  </Layout>, scene.duration);
}
