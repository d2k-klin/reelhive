import {Mascot} from './common';
import {stages} from './help-text';
import type {NodeState, RunEvent} from '../stores/events';
import {latestQualityResults, qualitySummary} from './ProductionProgress';

export function runGuidance(status: string, nodes: Record<string, NodeState> = {}, queue?: number | null, events:RunEvent[]=[], level:string='high'): [string, string] {
  if(status==='stopped') {
    const failures=latestQualityResults(events).map(qualitySummary).filter(result=>!result.passed);
    if(failures.length) return [failures.length===1 ? `${failures[0].label} is holding up video creation.` : `${failures.length} quality checks need attention.`, failures.map(result=>result.detail).join(' ')];
  }
  switch (status) {
    case 'editing': return ['Your brief is waiting for you.', 'Choose New video or duplicate this brief from Runs to finish setup and start writing.'];
    case 'awaiting_script': return ['Your story is ready for a read-through.', 'Edit the spoken words, then approve the script. Next, the scene agent will design the visuals while narration and music are prepared.'];
    case 'awaiting_scenes': if(level!=='high') return ['Your changes are ready to continue.', 'Save your scene edits, then continue production. The agents check images automatically; individual image approval is only needed in High customization.']; return ['You are the director now.', 'Select a scene, adjust its text or voice, save your edits, then approve every image. Next comes quality review and video creation.'];
    case 'queued': return [queue ? `Your production is waiting in position ${queue}.` : 'Your production is waiting for a free slot.', 'Another production is using the studio. Your saved choices will continue when the slot is free.'];
    case 'regenerating': return ['The agent is revising your saved work.', 'Wait for the editor to return, then review the new version before approving it.'];
    case 'done': return ['Your video is ready.', 'Watch it through, then download the MP4. Keep the run bundle if you want the script, scene settings, and media too.'];
    case 'stopped': return ['The video needs another look before it can continue.', 'Review the quality report and scene choices, save corrections, then continue production for another check.'];
    case 'failed': return ['Production hit a problem.', 'Check your setup and connection in Settings. The run log in its folder contains details. Fix the cause before resuming saved progress.'];
    case 'cancelled': return ['Production has stopped at a safe point.', 'Completed work is saved. Resume when you are ready, or return to Runs to start a different brief.'];
    case 'interrupted': return ['The last session ended before the video was finished.', 'Resume from saved progress when you are ready. Any unfinished stage may run again.'];
  }
  const active = Object.entries(nodes).filter(([, node]) => node.status === 'running').map(([name]) => stages[name]).filter(Boolean);
  if (active.length) return [active.map(stage => stage.doing).join(' '), active[0].next];
  if (status === 'drafting') return [stages.script.doing, stages.script.next];
  if (status === 'capturing') return ['Your app pages are being captured.', 'Next, inspect the previews and check that private details are hidden.'];
  return ['Your production is moving through its saved stages.', 'The progress view will explain each stage as it starts. You can leave this page while the studio stays open.'];
}

export function Guide({title, next, variant = 'working'}: {title: string; next: string; variant?: 'working' | 'presenting' | 'inspecting' | 'walking'}) {
  return <aside className="tutorial-guide" aria-label="Mr.D’s guide"><Mascot variant={variant}/><div><span className="eyebrow">MR.D’S GUIDE</span><p className="guide-now" role="status" aria-live="polite">{title}</p><p>{next}</p></div></aside>;
}
