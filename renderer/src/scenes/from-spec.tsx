/** @jsxImportSource @revideo/2d/lib */
import {makeScene2D, Rect, Img} from '@revideo/2d';
import {useScene} from '@revideo/core';
import {checkIntro, checkScene, type Spec} from '../spec';
import {addCreditCorner, creditEnd} from '../templates/credit';
import {imageFull} from '../templates/image-full';
import {introCard} from '../templates/intro';
import {TEMPLATES} from '../templates';
import {currentTheme} from '../themes/default';

export default makeScene2D('from-spec', function* (view) {
  const spec = useScene().variables.get('spec', null as unknown as Spec)();
  const theme = currentTheme();
  view.add(<Rect width={view.width()} height={view.height()} fill={theme.background} />);
  if (spec.theme?.logo) {
    const logo = new Img({src: spec.theme.logo, x: view.width() * 0.4, y: -view.height() * 0.42});
    yield logo.toPromise();
    const natural = logo.naturalSize();
    logo.size(natural.scale(Math.min(view.width() * 0.09 / natural.x, view.height() * 0.07 / natural.y)));
    view.add(logo);
  }
  if (spec.credit?.mode === 'corner') addCreditCorner(view);
  if (spec.intro) yield* introCard(view, checkIntro(spec.intro));
  for (const scene of spec.scenes) {
    checkScene(scene);
    yield* (scene.visual ? imageFull : TEMPLATES[scene.template])(view, scene);
  }
  if (spec.credit?.mode === 'end') yield* creditEnd(view, spec.credit);
});
