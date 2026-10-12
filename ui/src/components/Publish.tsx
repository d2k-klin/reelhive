// Publishing in the studio: pick platforms, draft the posts, edit them, and post only after an explicit
// confirmation. Accounts are signed in from Settings (or here, when one is missing) and are per machine.
import {useEffect, useState} from 'react';
import {useQuery, useQueryClient} from '@tanstack/react-query';
import {ExternalLink, LogIn, LogOut, Send, Sparkles} from 'lucide-react';
import {request} from '../api/client';
import type {components} from '../api/schema';
import {ErrorNote, Field} from './common';
import {Button, Help} from './Help';

type Job = components['schemas']['PublishJob'];
type Posts = components['schemas']['PostCopy'];
type Platform = Job['platforms'][number];
export interface AccountRow {
  platform: Platform; title: string; configured: boolean; env: string[]; setup: string; redirect_uri: string;
  account: {name: string; expires_at: number | null} | null;
}

const PLATFORMS: Platform[] = ['youtube', 'linkedin', 'tiktok', 'instagram'];
const TITLES: Record<Platform, string> = {youtube: 'YouTube', linkedin: 'LinkedIn', tiktok: 'TikTok', instagram: 'Instagram'};

export function useAccounts() {
  return useQuery({queryKey: ['publish-accounts'], queryFn: () => request<AccountRow[]>('/publish/accounts')});
}

/** Sign in: the server listens for the redirect; the consent page opens in a new tab and we poll until done. */
export function useConnect(onDone: () => void) {
  const [waiting, setWaiting] = useState<Platform | null>(null);
  const [error, setError] = useState<unknown>(null);
  const connect = async (platform: Platform) => {
    setError(null);
    try {
      const {id, url} = await request<{id: string; url: string}>(`/publish/accounts/${platform}/connect`, 'POST');
      window.open(url, '_blank', 'noopener');
      setWaiting(platform);
      for (let i = 0; i < 300; i++) {
        await new Promise(resolve => setTimeout(resolve, 2000));
        const state = await request<{status: string; error?: string}>(`/publish/connect/${id}`);
        if (state.status === 'connected') break;
        if (state.status === 'failed') throw new Error(state.error || 'Sign-in failed');
      }
    } catch (e) { setError(e); } finally { setWaiting(null); onDone(); }
  };
  return {connect, waiting, error};
}

export function Accounts() {
  const accounts = useAccounts();
  const {connect, waiting, error} = useConnect(() => accounts.refetch());
  return <div className="accounts">
    {accounts.data?.map(row => <div className="provider" key={row.platform}>
      <span className={`provider-light ${row.account ? 'ready' : ''}`}/>
      <strong>{row.title}</strong>
      <small>{row.account ? `Signed in as ${row.account.name}` : row.configured ? 'Not signed in' : `Set ${row.env.join(' and ')}`}</small>
      {row.account
        ? <Button className="secondary compact" onClick={async () => {await request(`/publish/accounts/${row.platform}`, 'DELETE'); accounts.refetch();}}><LogOut size={14}/>Sign out</Button>
        : <Button className="secondary compact" disabled={!row.configured || waiting !== null} onClick={() => connect(row.platform)}><LogIn size={14}/>{waiting === row.platform ? 'Waiting…' : 'Connect'}</Button>}
    </div>)}
    {accounts.data?.[0] && <p className="muted">Register <code>{accounts.data[0].redirect_uri}</code> as the redirect URI in each developer app. Sign-ins stay on this computer.</p>}
    <ErrorNote error={error || accounts.error}/>
  </div>;
}

function CopyFields({platform, posts, onChange}: {platform: Platform; posts: Posts; onChange: (p: Posts) => void}) {
  const set = (patch: Record<string, unknown>) => onChange({...posts, [platform]: {...(posts as any)[platform], ...patch}});
  const value = (posts as any)[platform] || {};
  if (platform === 'youtube') return <>
    <Field label="YouTube title"><input maxLength={100} value={value.title || ''} onChange={e => set({title: e.target.value})}/></Field>
    <Field label="YouTube description"><textarea rows={5} maxLength={5000} value={value.description || ''} onChange={e => set({description: e.target.value})}/></Field>
    <Field label="YouTube tags"><input value={(value.tags || []).join(', ')} onChange={e => set({tags: e.target.value.split(',').map((t: string) => t.trim()).filter(Boolean)})}/></Field>
  </>;
  if (platform === 'linkedin') return <>
    <Field label="LinkedIn post"><textarea rows={6} maxLength={2800} value={value.commentary || ''} onChange={e => set({commentary: e.target.value})}/></Field>
    <Field label="LinkedIn video title"><input maxLength={100} value={value.title || ''} onChange={e => set({title: e.target.value})}/></Field>
  </>;
  return <Field label={`${TITLES[platform]} caption`}><textarea rows={4} maxLength={2200} value={value.caption || ''} onChange={e => set({caption: e.target.value})}/></Field>;
}

export function PublishPanel({runId}: {runId: string}) {
  const queryClient = useQueryClient();
  const accounts = useAccounts();
  // While a draft or publish runs in the background, poll until the job differs from what it was when we asked.
  const [baseline, setBaseline] = useState<string | null>(null);
  const pending = baseline !== null;
  const job = useQuery({
    queryKey: ['publish', runId],
    queryFn: () => request<Job | null>(`/runs/${runId}/publish`),
    refetchInterval: query => query.state.data?.status === 'publishing' || pending ? 2000 : false,
  });
  const [chosen, setChosen] = useState<Platform[]>([]);
  const [posts, setPosts] = useState<Posts | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const {connect, waiting} = useConnect(() => accounts.refetch());
  const data = job.data;
  useEffect(() => {
    if (data?.posts) setPosts(data.posts);
    if (pending && JSON.stringify(data ?? null) !== baseline && data?.status !== 'publishing') setBaseline(null);
  }, [data]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (data?.platforms && !chosen.length) setChosen(data.platforms); }, [data]); // eslint-disable-line react-hooks/exhaustive-deps
  const signedIn = (p: Platform) => !!accounts.data?.find(a => a.platform === p)?.account;
  const act = async (work: () => Promise<unknown>) => {
    setError(null);
    const before = JSON.stringify(data ?? null);
    try { await work(); setBaseline(before); await queryClient.invalidateQueries({queryKey: ['publish', runId]}); } catch (e) { setError(e); }
  };
  const draft = () => act(() => request(`/runs/${runId}/publish/draft`, 'POST', {platforms: chosen}));
  const save = async () => { if (posts) { setError(null); try { await request(`/runs/${runId}/publish/posts`, 'PUT', posts); await job.refetch(); } catch (e) { setError(e); } } };
  const publish = () => act(async () => { await save(); await request(`/runs/${runId}/publish`, 'POST', {confirm: true}); setConfirming(false); });
  const live = data && Object.entries(data.results || {}).filter(([, r]) => r?.status === 'published' || r?.status === 'failed');
  return <section className="publish-panel" aria-label="Publish">
    <div className="section-title"><span>03</span><div><h2>Publish</h2><p>Draft the post for each platform, review it, then publish under your own accounts.</p></div><Help label="Publish">ReelHive drafts a title, description or caption for each platform from your brief and narration. Nothing is posted until you confirm. The video and its subtitles go straight from this computer to each platform.</Help></div>
    <div className="toggles">{PLATFORMS.map(p => <span className="toggle" key={p}><label className="check"><input type="checkbox" checked={chosen.includes(p)} onChange={e => setChosen(e.target.checked ? [...chosen, p] : chosen.filter(x => x !== p))}/>{TITLES[p]}</label>{!signedIn(p) && <Button type="button" className="secondary compact" disabled={waiting !== null} onClick={() => connect(p)}><LogIn size={12}/>{waiting === p ? 'Waiting…' : 'Connect'}</Button>}</span>)}</div>
    <div className="toolbar"><Button className="secondary" disabled={!chosen.length || pending} onClick={draft}><Sparkles size={16}/>{data?.posts ? 'Draft again' : 'Draft posts'}</Button></div>
    {data?.warnings?.map(w => <p className="notice" key={w}>{w}</p>)}
    {data?.status === 'blocked' && <div className="gate-list">{data.failures?.map(f => <div className="gate-failed" key={f}><strong>Not ready</strong><span>{f}</span></div>)}</div>}
    {posts && data?.status !== 'blocked' && <>
      {data?.platforms.map(p => <fieldset className="post-copy" key={p}><legend>{TITLES[p]}</legend><CopyFields platform={p} posts={posts} onChange={setPosts}/></fieldset>)}
      <div className="toolbar"><Button className="secondary" onClick={save}>Save edits</Button>
        {!confirming
          ? <Button disabled={pending || data?.status === 'published'} onClick={() => setConfirming(true)}><Send size={16}/>Publish…</Button>
          : <div role="alertdialog" aria-label="Confirm publishing" className="confirm"><span>Post this video publicly to {data?.platforms.map(p => TITLES[p]).join(', ')} under your accounts?</span><Button onClick={publish}><Send size={16}/>Yes, publish</Button><Button className="secondary" onClick={() => setConfirming(false)}>Cancel</Button></div>}
      </div>
    </>}
    {data?.status === 'publishing' && <p className="muted">Publishing… each platform appears below as it finishes.</p>}
    {live && live.length > 0 && <ul className="publish-results">{live.map(([p, r]) => <li key={p} className={r?.status}>
      <strong>{TITLES[p as Platform]}</strong>{r?.status === 'published'
        ? <>{r.url ? <a href={r.url} target="_blank" rel="noreferrer">View post <ExternalLink size={12}/></a> : <span>Sent</span>}{r.note && <small>{r.note}</small>}</>
        : <span className="error">{r?.error}</span>}
    </li>)}</ul>}
    <ErrorNote error={error || job.error}/>
  </section>;
}
