import {Background, Controls, ReactFlow, type Edge, type Node} from '@xyflow/react';
import {Check, CircleAlert} from 'lucide-react';
import {stages} from './help-text';
import type {NodeState, RunEvent} from '../stores/events';
import {Help} from './Help';

const positions: Record<string, [number, number]> = {script:[0,100], scenes:[210,0], visuals:[420,0], narrate:[210,110], music:[210,220], timing:[630,100], critic:[840,100], fix:[1050,0], recheck:[1260,0], render:[1470,100]};
const edges: Edge[] = [['script','scenes'],['script','narrate'],['script','music'],['scenes','visuals'],['visuals','timing'],['narrate','timing'],['music','timing'],['timing','critic'],['critic','render'],['critic','fix'],['fix','recheck'],['recheck','render']].map(([source,target],i)=>({id:`e${i}`,source,target}));
const checks: Record<string, string> = {duration:'Video length', pace:'Speaking pace', closing:'Closing message', features:'Feature coverage', text_limits:'Readable text', audio:'Matching narration', images:'Image quality', product_ui:'Authentic product images', voice_fit:'Voice fits the scene', image_approval:'Image approvals'};
export function qualitySummary(event: RunEvent) {
  if (event.type === 'critic.verdict') return {label:'Story review', passed:event.data.passed === true, detail:event.data.passed ? 'The story is ready to continue.' : 'The review agent requested improvements before video creation.'};
  if (event.type === 'fix.diff') return {label:'Scene revisions', passed:true, detail:`The repair agent updated ${Array.isArray(event.data.changes) ? event.data.changes.length : 'the affected'} scenes for another check.`};
  return {label:checks[event.data.check] || 'Production check', passed:event.data.passed === true, detail:event.data.passed ? 'Passed — this requirement is met.' : 'Needs attention — review this requirement before continuing.'};
}

export function ProductionProgress({nodes: state, events}: {nodes: Record<string, NodeState>; events: RunEvent[]}) {
  const nodes: Node[] = Object.entries(stages).map(([name, stage]) => ({id:name, position:{x:positions[name][0], y:positions[name][1]}, data:{label:<><span className={`node-dot ${state[name]?.status || 'waiting'}`}/><strong>{stage.label}</strong><small>{state[name]?.status || 'waiting'}</small></>}, className:`flow-node ${state[name]?.status || 'waiting'}`}));
  return <><section className="graph-section"><div className="section-title"><span>01</span><div><h2>Production progress</h2><p>Writing, scenes, voice, and music become your finished video.</p></div><Help label="Production progress">Some stages work at the same time. Completed work is saved. A skipped repair stage means no repair was needed.</Help></div><div className="graph"><ReactFlow nodes={nodes} edges={edges} fitView nodesDraggable={false} nodesConnectable={false} elementsSelectable={false} proOptions={{hideAttribution:true}}><Background gap={22}/><Controls showInteractive={false}/></ReactFlow></div><div className="agent-list">{Object.entries(stages).map(([name, stage]) => <article key={name} className={state[name]?.status || 'waiting'}><header><span className={`node-dot ${state[name]?.status || 'waiting'}`}/><strong>{stage.label}</strong><small>{state[name]?.status || 'waiting'}</small></header><p>{state[name]?.status === 'running' ? stage.doing : state[name]?.status === 'done' ? 'This stage is complete and saved.' : state[name]?.status === 'failed' ? 'This stage needs attention. Check the run log for details.' : state[name]?.status === 'skipped' ? 'This stage was not needed.' : stage.next}</p>{state[name]?.seconds !== undefined && <footer>{state[name].seconds}s elapsed</footer>}</article>)}</div></section><QualityChecks events={events}/></>;
}

export function QualityChecks({events}: {events:RunEvent[]}) {
  const results = events.filter(e => ['gate.result','critic.verdict','fix.diff'].includes(e.type));
  return <section><div className="section-title"><span>02</span><div><h2>Quality checks</h2><p>The story and video must meet these requirements before finishing.</p></div></div><div className="gate-list">{results.map(event => {const result=qualitySummary(event); return <div key={event.id} className={result.passed ? '' : 'gate-failed'}>{result.passed ? <Check size={16} aria-label="Passed"/> : <CircleAlert size={16} aria-label="Needs attention"/>}<strong>{result.label}</strong><span>{result.detail}</span></div>;})}{!results.length && <p className="muted">Checks appear once the scenes and narration are ready.</p>}</div></section>;
}
