import React from 'react';
import ReactDOM from 'react-dom/client';
import {BrowserRouter, NavLink, Route, Routes, Link} from 'react-router-dom';
import {QueryClient, QueryClientProvider, useQuery} from '@tanstack/react-query';
import {Film, Plus, Settings, SunMoon} from 'lucide-react';
import {useEffect, useState} from 'react';
import {request} from './api/client';
import {Mascot} from './components/common';
import {BriefPage} from './pages/Brief';
import {RunsPage} from './pages/Runs';
import {RunPage} from './pages/Run';
import {SettingsPage} from './pages/Settings';
import './style.css';
import './a11y.css';
import './tutorial.css';
class ErrorBoundary extends React.Component<{children: React.ReactNode}, {error: Error | null}> {
 state = {error: null as Error | null};
 static getDerivedStateFromError(error: Error) { return {error}; }
 render() { return this.state.error ? <div role="alert" className="error" style={{margin: '2rem'}}>The studio could not display this page. Reload to recover saved work; unsaved edits may be lost. <button onClick={() => location.reload()}>Reload</button></div> : this.props.children; }
}
const queryClient = new QueryClient({defaultOptions:{queries:{retry:1, refetchOnWindowFocus:false}}});
function App() {
 const [theme,setTheme]=useState(localStorage.getItem('reelhive-theme')||'system');
 useEffect(()=>{const media=matchMedia('(prefers-color-scheme: dark)'); const apply=()=>document.documentElement.dataset.theme=theme==='system'?(media.matches?'dark':'light'):theme;apply();media.addEventListener('change',apply);localStorage.setItem('reelhive-theme',theme);return()=>media.removeEventListener('change',apply);},[theme]);
 useEffect(()=>{document.querySelector('.sidebar')?.setAttribute('aria-label','Primary navigation');},[]);
 const health=useQuery({queryKey:['health'],queryFn:()=>request<{status:string}>('/health')});
 return <div className="app"><a className="skip" href="#main">Skip to content</a><aside className="sidebar"><Link className="brand" to="/"><span className="brandmark">R</span>ReelHive<span className="version">0.3</span></Link><div className="workspace-label">YOUR VIDEO STUDIO</div><nav><NavLink to="/" end><Plus size={19}/>New video</NavLink><NavLink to="/runs"><Film size={19}/>Runs</NavLink><NavLink to="/settings"><Settings size={19}/>Settings</NavLink></nav><footer><Mascot/><strong>ReelHive by Mr.D</strong><small>Curious by nature. Always building.</small><label className="theme-switch"><SunMoon size={16}/><span className="sr-only">Appearance</span><select aria-label="Appearance" value={theme} onChange={e=>setTheme(e.target.value)}><option value="system">System theme</option><option value="light">Light theme</option><option value="dark">Dark theme</option></select></label></footer></aside><div className="content"><header className="topbar"><span><span className={`dot ${health.isSuccess?'ready':''}`}/> {health.isSuccess?'Local workspace':'Connecting to workspace'}</span><Link to="/settings">Agent settings <span aria-hidden>↗</span></Link></header><main id="main"><Routes><Route path="/" element={<BriefPage/>}/><Route path="/runs" element={<RunsPage/>}/><Route path="/runs/:id" element={<RunPage/>}/><Route path="/settings" element={<SettingsPage/>}/></Routes></main></div></div>;
}
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><ErrorBoundary><QueryClientProvider client={queryClient}><BrowserRouter><App/></BrowserRouter></QueryClientProvider></ErrorBoundary></React.StrictMode>);
