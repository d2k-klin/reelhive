import {makeScene2D, Rect} from '@revideo/2d';
import {useScene} from '@revideo/core';
import {checkScene, type Spec} from '../spec';
import {addCreditCorner, creditEnd} from '../templates/credit';
import {TEMPLATES} from '../templates';
import {theme} from '../themes/default';

export default makeScene2D('from-spec', function* (view) {
  const spec = useScene().variables.get('spec', null as unknown as Spec)();
  view.add(<Rect width={view.width()} height={view.height()} fill={theme.background} />);
  if (spec.credit?.mode === 'corner') addCreditCorner(view);
  for (const scene of spec.scenes) {
    yield* TEMPLATES[checkScene(scene).template](view, scene);
  }
  if (spec.credit?.mode === 'end') yield* creditEnd(view, spec.credit);
});
