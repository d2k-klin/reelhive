import type {ReactNode} from 'react';
import {LoaderCircle, Check, Circle, AlertCircle} from 'lucide-react';
import mascot from '@brand/mr-d-laptop.webp';
import type {Brief} from '../api/client';
export function Field({label, children, hint}: {label: string; children: ReactNode; hint?: string}) {return <label className="field"><span>{label}</span>{children}{hint && <small>{hint}</small>}</label>;}
export function ErrorNote({error}: {error: unknown}) {return error ? <p role="alert" className="error"><AlertCircle size={18}/>{error instanceof Error ? error.message : String(error)}</p> : null;}
export function Status({value}: {value: string}) {const busy=['drafting','producing','running','queued','regenerating'].includes(value);return <span className={`status ${value}`}>{busy ? <LoaderCircle size={14} className="spin"/> : value==='done' ? <Check size={14}/> : <Circle size={12}/>} {value.replaceAll('_',' ')}</span>;}
export function Mascot({className=''}: {className?: string}) {return <img className={`mascot ${className}`} src={mascot} alt=""/>;}
export function VoiceFields({value, onChange}: {value: NonNullable<Brief['voice']>; onChange: (v: NonNullable<Brief['voice']>)=>void}) {return <div className="row"><Field label="Voice"><select value={value.gender} onChange={e=>onChange({...value,gender:e.target.value as 'male'|'female'})}><option>female</option><option>male</option></select></Field><Field label="Accent"><select value={value.accent} onChange={e=>onChange({...value,accent:e.target.value as 'american'|'british'})}><option>american</option><option>british</option></select></Field><Field label="Speed"><input type="number" min="0.8" max="1.2" step="0.05" value={value.speed} onChange={e=>onChange({...value,speed:+e.target.value})}/></Field></div>;}
