import {Check, CircleAlert} from 'lucide-react';
import {stages} from './help-text';
import type {NodeState, RunEvent} from '../stores/events';
import {Help} from './Help';

const checks: Record<string, string> = {duration:'Video length', pace:'Speaking pace', closing:'Closing message', features:'Feature coverage', text_limits:'Readable text', audio:'Matching narration', images:'Image quality', product_ui:'Authentic product images', voice_fit:'Voice fits the scene', image_approval:'Image approvals'};
export function qualitySummary(event: RunEvent) {
  if (event.type === 'critic.verdict') return {label:'Story review', passed:event.data.passed === true, detail:event.data.passed ? 'The story is ready to continue.' : 'The review agent requested improvements before video creation.'};
  if (event.type === 'fix.diff') return {label:'Scene revisions', passed:true, detail:`The repair agent updated ${Array.isArray(event.data.changes) ? event.data.changes.length : 'the affected'} scenes for another check.`};
  const passed=event.data.passed===true;
  let detail=passed ? 'Passed — this requirement is met.' : 'Needs attention — review this requirement before continuing.';
  if(event.data.check==='duration' && typeof event.data.value==='number' && Number.isFinite(event.data.value)) {
    const target=String(event.data.threshold||'').match(/^(\d+(?:\.\d+)?)s ±(\d+(?:\.\d+)?)%$/);
    if(target) {
      const seconds=Number(target[1]), tolerance=Number(target[2])/100;
      detail=`${event.data.value.toFixed(1)}s produced; target ${seconds}s (allowed ${(seconds*(1-tolerance)).toFixed(1)}–${(seconds*(1+tolerance)).toFixed(1)}s).`;
      if(!passed) detail+=event.data.value>seconds ? ' Shorten narration or increase scene voice speed, then save scenes and approve again.' : 'Add narration or lengthen scenes, then save scenes and approve again.';
    }
  }
  return {label:checks[event.data.check] || 'Production check', passed, detail};
}

/** Rechecks supersede earlier failures; keep the current result for each requirement. */
export function latestQualityResults(events:RunEvent[]) {
  const latest=new Map<string,RunEvent>();
  for(const event of events) {
    if(event.type==='gate.result') latest.set(`gate:${event.data.check}`,event);
    else if(['critic.verdict','fix.diff'].includes(event.type)) latest.set(event.type,event);
  }
  return [...latest.values()];
}

const phases = [
  {title:'Story', note:'Research, then write', nodes:['research','script']},
  {title:'Create', note:'Scenes, voice & music in parallel', nodes:['scenes','visuals','narrate','music']},
  {title:'Timing', note:'Fit the narration', nodes:['timing']},
  {title:'Review', note:'Repair only if needed', nodes:['critic','fix','recheck']},
  {title:'Video', note:'Create the final cut', nodes:['render']},
];
const statusText: Record<string,string> = {waiting:'Waiting', running:'In progress', done:'Complete', failed:'Needs attention', skipped:'Not needed'};

export function ProductionProgress({nodes, events}: {nodes: Record<string, NodeState>; events: RunEvent[]}) {
  return <><section className="graph-section" aria-label="Production progress">
    <div className="section-title"><span>01</span><div><h2>Production progress</h2><p>Follow your story from the first draft to the final cut.</p></div><Help label="Production progress">Read from left to right, or top to bottom on a phone. Scenes, voice, and music can run together. Visuals follow scene design. Repairs run only when review asks for changes.</Help></div>
    <ol className="production-path">
      {phases.map((phase,index)=><li className="production-phase" key={phase.title}>
        <header><span className="phase-number">{String(index+1).padStart(2,'0')}</span><h3>{phase.title}</h3></header>
        <p className="phase-note">{phase.note}</p>
        <ul>{phase.nodes.map(name=>{
          const stage=stages[name];
          const state=nodes[name]?.status||'waiting';
          return <li className={`production-task ${state}`} key={name}>
            <span className={`node-dot ${state}`} aria-hidden/>
            <div><strong>{stage.label}</strong><small>{statusText[state]||'Waiting'}{nodes[name]?.seconds!==undefined ? ` · ${Math.round(nodes[name].seconds!)}s` : ''}</small></div>
            <Help label={stage.label}>{state==='running'?stage.doing:stage.next}</Help>
          </li>;
        })}</ul>
      </li>)}
    </ol>
  </section><QualityChecks events={events}/></>;
}

export function QualityChecks({events}: {events:RunEvent[]}) {
  const results = latestQualityResults(events);
  return <section><div className="section-title"><span>02</span><div><h2>Quality checks</h2><p>The story and video must meet these requirements before finishing.</p></div></div><div className="gate-list">{results.map(event => {const result=qualitySummary(event); return <div key={event.id} className={result.passed ? '' : 'gate-failed'}>{result.passed ? <Check size={16} aria-label="Passed"/> : <CircleAlert size={16} aria-label="Needs attention"/>}<strong>{result.label}</strong><span>{result.detail}</span></div>;})}{!results.length && <p className="muted">Checks appear once the scenes and narration are ready.</p>}</div></section>;
}
