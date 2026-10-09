import {createStore} from 'zustand/vanilla';
export type RunEvent = {id: number; ts: number; type: string; data: Record<string, any>};
export type NodeState = {status: string; text: string; tasks: string[]; seconds?: number; tokens?: number; error?: string; provider?: string; model?: string};
export function createEventStore() {
 return createStore<{last: number; nodes: Record<string, NodeState>; events: RunEvent[]; connected: boolean; accept: (event: RunEvent) => void; connect: (value: boolean) => void}>((set) => ({
  last: 0, nodes: {}, events: [], connected: false, connect: (connected) => set({connected}),
  accept: (event) => set(state => {
   if (event.id <= state.last) return state;
   const nodes = {...state.nodes}; const name = event.data.node;
   if (name) {
    const node = {...(nodes[name] || {status: 'waiting', text: '', tasks: []})};
    if (event.type === 'node.started') { node.status = 'running'; node.text = ''; node.tasks = []; }
    if (event.type === 'node.finished') Object.assign(node, event.data, {status: event.data.status === 'completed' ? 'done' : 'failed'});
    // Later approval graphs omit already completed stages; that is reuse, not unused work.
    if (event.type === 'node.skipped') node.status = node.status === 'done' || event.data.reason === 'restored checkpoint' ? 'done' : 'skipped';
    if (event.type === 'agent.text') node.text = (node.text + event.data.text).slice(-20000);
    if (event.type === 'node.task') { node.tasks = [...node.tasks, event.data.task].slice(-30); if (event.data.provider) Object.assign(node, event.data); }
    nodes[name] = node;
   }
   return {last: event.id, nodes, events: [...state.events, event].slice(-1000)};
  })
 }));
}
