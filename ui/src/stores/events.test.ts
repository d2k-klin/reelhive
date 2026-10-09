import {describe, expect, it} from 'vitest';
import {createEventStore} from './events';

describe('run event store', () => {
  it('replays monotonic events and ignores duplicates', () => {
    const store = createEventStore();
    store.getState().accept({id: 1, ts: 1, type: 'node.started', data: {node: 'script'}});
    store.getState().accept({id: 2, ts: 2, type: 'agent.text', data: {node: 'script', text: 'hello'}});
    store.getState().accept({id: 2, ts: 2, type: 'agent.text', data: {node: 'script', text: 'duplicate'}});
    store.getState().accept({id: 3, ts: 3, type: 'node.finished', data: {node: 'script', status: 'completed', tokens: 42}});
    expect(store.getState().last).toBe(3);
    expect(store.getState().events).toHaveLength(3);
    expect(store.getState().nodes.script).toMatchObject({status: 'done', text: 'hello', tokens: 42});
  });
  it('keeps completed work complete when a later approval graph skips it', () => {
    const store=createEventStore();
    store.getState().accept({id:1,ts:1,type:'node.finished',data:{node:'scenes',status:'completed'}});
    store.getState().accept({id:2,ts:2,type:'node.skipped',data:{node:'scenes'}});
    store.getState().accept({id:3,ts:3,type:'node.skipped',data:{node:'fix'}});
    expect(store.getState().nodes.scenes.status).toBe('done');
    expect(store.getState().nodes.fix.status).toBe('skipped');
  });
});
