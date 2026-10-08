import {useMemo, useState} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {Link, useNavigate} from 'react-router-dom';
import {Copy, Download, FolderOpen, Search, Trash2} from 'lucide-react';
import {fileUrl, request, type Run} from '../api/client';
import {ErrorNote, Mascot, Status} from '../components/common';

export function RunsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('all');
  const [provider, setProvider] = useState('all');
  const runs = useQuery({queryKey: ['runs'], queryFn: () => request<Run[]>('/runs'), refetchInterval: 2500});
  const remove = useMutation({mutationFn: (id: string) => request<void>(`/runs/${id}`, 'DELETE'), onSuccess: () => queryClient.invalidateQueries({queryKey: ['runs']})});
  const shown = useMemo(() => (runs.data || []).filter(run => {
    const text = `${run.brief?.storyline || ''} ${run.id}`.toLowerCase();
    return text.includes(search.toLowerCase()) && (status === 'all' || run.status === status) && (provider === 'all' || run.provider === provider);
  }), [runs.data, search, status, provider]);
  return <><div className="page-heading"><div><div className="eyebrow">PRODUCTIONS</div><h1>Runs</h1><p>Every draft, decision, and finished film stays on this machine.</p></div><Link className="button" to="/">New video</Link></div>
    <div className="filters"><label className="search"><Search size={17}/><span className="sr-only">Search runs</span><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search productions"/></label><select aria-label="Filter by status" value={status} onChange={e=>setStatus(e.target.value)}><option value="all">All statuses</option>{['drafting','awaiting_script','awaiting_scenes','queued','producing','done','stopped','failed','cancelled','interrupted'].map(v=><option key={v}>{v}</option>)}</select><select aria-label="Filter by provider" value={provider} onChange={e=>setProvider(e.target.value)}><option value="all">All providers</option>{['claude','bedrock','openai','ollama','copilot'].map(v=><option key={v}>{v}</option>)}</select></div>
    <ErrorNote error={runs.error || remove.error}/>
    {runs.isLoading ? <p className="muted">Loading runs…</p> : shown.length === 0 ? <div className="empty"><Mascot variant="walking"/><div><h2>No videos here yet</h2><p>Start with a brief. Mr.D will take it from script to final cut.</p><Link className="button" to="/">Start the first video</Link></div></div> : <div className="run-table" role="table" aria-label="Video runs"><div className="run-row run-head" role="row"><span>Production</span><span>Level</span><span>Provider</span><span>Status</span><span>Actions</span></div>{shown.map(run=><div className="run-row" role="row" key={run.id} onClick={()=>navigate(`/runs/${run.id}`)}><div><strong>{run.brief?.storyline || run.id}</strong><small>{run.id.slice(0,8)} · {run.brief?.duration}s · {run.brief?.format}</small></div><span>{run.brief?.level}</span><span>{run.provider}</span><Status value={run.status}/><div className="row-actions" onClick={e=>e.stopPropagation()}>{run.video&&<a className="icon" aria-label="Download video" href={fileUrl(run.id,'video.mp4')}><Download size={16}/></a>}<button className="icon" aria-label="Duplicate as new brief" onClick={()=>{localStorage.setItem('reelhive-draft',JSON.stringify(run.brief));navigate('/');}}><Copy size={16}/></button><button className="icon" aria-label="Reveal folder" onClick={()=>request(`/runs/${run.id}/reveal`,'POST')}><FolderOpen size={16}/></button><button className="icon danger" aria-label="Delete run" onClick={()=>{if(confirm(`Delete ${run.id}?`))remove.mutate(run.id);}}><Trash2 size={16}/></button></div></div>)}</div>}
  </>;
}
