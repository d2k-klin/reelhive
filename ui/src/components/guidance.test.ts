import {describe, expect, it} from 'vitest';
import {runGuidance} from './Guide';
import {latestQualityResults, qualitySummary} from './ProductionProgress';

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
  it('explains the logged duration blocker using measured values and allowed limits',()=>{
    const event={id:62,ts:1,type:'gate.result',data:{check:'duration',passed:false,value:98.6,threshold:'92s ±5%'}};
    const result=qualitySummary(event);
    expect(result.detail).toContain('98.6s produced; target 92s (allowed 87.4–96.6s)');
    expect(result.detail).toContain('save scenes and approve again');
    expect(runGuidance('stopped',{},null,[event])).toEqual(['Video length is holding up video creation.',result.detail]);
  });
  it('shows the recheck instead of stale failures from before the repair',()=>{
    const events=[
      {id:41,ts:1,type:'gate.result',data:{check:'duration',passed:false,value:111.37,threshold:'92s ±5%'}},
      {id:42,ts:1,type:'gate.result',data:{check:'audio',passed:false}},
      {id:62,ts:2,type:'gate.result',data:{check:'duration',passed:false,value:98.6,threshold:'92s ±5%'}},
      {id:66,ts:2,type:'gate.result',data:{check:'audio',passed:true}},
    ];
    expect(latestQualityResults(events).map(event=>event.id)).toEqual([62,66]);
    const [now,next]=runGuidance('stopped',{},null,events);
    expect(now).toBe('Video length is holding up video creation.');
    expect(next).not.toContain('111.4');
  });
  it('does not ask Low or Medium users to approve images during recovery',()=>{
    for(const level of ['low','medium']) {
      const [,next]=runGuidance('awaiting_scenes',{},null,[],level);
      expect(next).toContain('check images automatically');
      expect(next).not.toContain('approve every image');
    }
    expect(runGuidance('awaiting_scenes',{},null,[],'high')[1]).toContain('approve every image');
  });
});
