import {describe, expect, it} from 'vitest';
import {runGuidance} from './Guide';
import {qualitySummary} from './ProductionProgress';

describe('tutorial progress reflects the real run state',()=>{
  it('explains simultaneous work without inventing progress percentages',()=>{
    const active={status:'running',text:'internal model output',tasks:['ffmpeg']};
    const [now,next]=runGuidance('producing',{narrate:active,music:active});
    expect(now).toContain('spoken audio');expect(now).toContain('background track');
    expect(next).toContain('timing');expect(now).not.toMatch(/ffmpeg|internal|%/);
  });
  it('approval and failure states take priority over old running events',()=>{
    const nodes={render:{status:'running',text:'',tasks:[]}};
    expect(runGuidance('awaiting_scenes',nodes)[0]).toContain('director');
    expect(runGuidance('failed',nodes)[0]).toContain('problem');
    expect(runGuidance('queued',nodes,3)[0]).toContain('position 3');
  });
  it('failed quality checks are not presented as successful',()=>{
    const event={id:1,ts:1,type:'gate.result',data:{check:'voice_fit',passed:false,value:false}};
    expect(qualitySummary(event)).toMatchObject({label:'Voice fits the scene',passed:false});
    expect(qualitySummary(event).detail).toContain('Needs attention');
  });
});
