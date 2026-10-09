// M6 quick actions (UI plan §16). CopilotKit is used only here, and this module is lazy-loaded by the
// Script and Scenes screens, so removing CopilotKit touches nothing else.
//
// The `suggest` agent is an AG-UI endpoint on the local server (/api/agui/suggest). Its run streams one
// `propose_suggestions` tool call; CopilotKit executes it as a frontend tool and we render the validated
// arguments as buttons (generative UI). Applying a suggestion never goes through the agent: it calls the
// existing regenerate route, so the server stays the only place that changes a run.
import {HttpAgent} from '@ag-ui/client';
import {CopilotKitProvider, useAgent, useCopilotKit, useFrontendTool} from '@copilotkit/react-core/v2';
import {Lightbulb, RefreshCw, Undo2} from 'lucide-react';
import {useCallback, useEffect, useMemo, useState} from 'react';
import {token} from '../api/client';
import {type Suggestion, SuggestionsSchema} from './suggestions';

type Props = {
  runId: string;
  target: 'beat' | 'scene';
  index: number;
  /** Changes whenever the beat or scene changes, so its suggestions are refreshed (and cached server-side). */
  version: string;
  busy: boolean;
  canUndo: boolean;
  onApply: (suggestion: Suggestion) => void;
  onUndo: () => void;
};

export function SuggestionChips({runId, target, index, version, busy, canUndo, onApply, onUndo}: Props) {
  const {agent} = useAgent({agentId: 'suggest'});
  const {copilotkit} = useCopilotKit();
  const [chips, setChips] = useState<Suggestion[] | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useFrontendTool(
    {
      name: 'propose_suggestions',
      description: 'Show 3-4 quick-action buttons for the selected beat or scene.',
      parameters: SuggestionsSchema,
      followUp: false,
      handler: async args => {
        const parsed = SuggestionsSchema.safeParse(args); // never render or apply unvalidated tool output
        if (!parsed.success) {
          setError('The suggestions were malformed.');
          return 'rejected';
        }
        setChips(parsed.data.suggestions);
        return 'shown';
      },
    },
    [],
  );

  const ask = useCallback(
    async (fresh: boolean) => {
      if (!agent) return;
      setLoading(true);
      setError('');
      setChips(null);
      agent.setMessages([]);
      agent.setState({run_id: runId, target, index, fresh});
      try {
        const result = await copilotkit.runAgent({agent});
        void result;
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setLoading(false);
      }
    },
    [agent, copilotkit, runId, target, index],
  );

  useEffect(() => {
    void ask(false);
  }, [ask, version]);

  return (
    <div className="quick-actions" aria-live="polite">
      <div className="quick-actions-head">
        <Lightbulb size={15} aria-hidden />
        <strong>Quick actions</strong>
        <small>Suggested by the Editor agent for this {target}</small>
      </div>
      {loading && <p className="muted">Thinking of edits…</p>}
      {error && <p className="muted">{error}</p>}
      {chips && (
        <div className="chips" role="group" aria-label={`Suggestions for ${target} ${index}`}>
          {chips.map(chip => (
            <button key={chip.label} className="chip" title={chip.instruction} disabled={busy} onClick={() => onApply(chip)}>
              {chip.label}
              <span className="sr-only">: {chip.instruction}</span>
            </button>
          ))}
        </div>
      )}
      <div className="quick-actions-tools">
        <button className="link" disabled={busy || loading} onClick={() => void ask(true)}>
          <RefreshCw size={13} aria-hidden /> More ideas
        </button>
        {canUndo && (
          <button className="link" disabled={busy} onClick={onUndo}>
            <Undo2 size={13} aria-hidden /> Undo last change
          </button>
        )}
      </div>
    </div>
  );
}

export default function QuickActions(props: Props) {
  // One AG-UI agent, talking straight to the local endpoint: no CopilotKit runtime process, nothing remote.
  const agents = useMemo(
    () => ({suggest: new HttpAgent({url: '/api/agui/suggest', headers: {Authorization: `Bearer ${token()}`}})}),
    [],
  );
  return (
    <CopilotKitProvider selfManagedAgents={agents} showDevConsole={false}>
      <SuggestionChips {...props} />
    </CopilotKitProvider>
  );
}
