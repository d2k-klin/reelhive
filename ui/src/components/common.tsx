import {Children, cloneElement, isValidElement, useId, type ReactNode} from 'react';
import {LoaderCircle, Check, Circle, AlertCircle} from 'lucide-react';
import mascot from '@brand/mr-d-laptop.webp';
import walking from '@brand/mr-d-art-3.webp';
import working from '@brand/mr-d-art-5.webp';
import presenting from '@brand/mr-d-art-7.webp';
import inspecting from '@brand/mr-d-art-9.webp';
import type {Brief} from '../api/client';
import {Help} from './Help';
import {fieldHelp} from './help-text';
export function Field({label, children, hint}: {label: string; children: ReactNode; hint?: string}) {
 const id = useId();
 const controls = Children.toArray(children);
 const labelled = controls.some(child => isValidElement(child) && ['input','select','textarea'].includes(String(child.type)));
 const explanation = fieldHelp[label] || (label.startsWith('Duration') ? fieldHelp.Seconds : undefined);
 return <div className="field"><div className="field-heading">{labelled ? <label htmlFor={id}>{label}</label> : <span id={id}>{label}</span>}{explanation && <Help label={label}>{explanation}</Help>}</div>{controls.map(child => isValidElement<Record<string, unknown>>(child) && ['input','select','textarea'].includes(String(child.type)) ? cloneElement(child, {id, 'aria-describedby': hint ? `${id}-hint` : undefined}) : child)}{hint && <small id={`${id}-hint`}>{hint}</small>}</div>;
}
export function ErrorNote({error}: {error: unknown}) {return error ? <p role="alert" className="error"><AlertCircle size={18}/>{error instanceof Error ? error.message : String(error)}</p> : null;}
export function Status({value}: {value: string}) {const busy=['drafting','producing','running','queued','regenerating'].includes(value);return <span className={`status ${value}`}>{busy ? <LoaderCircle size={14} className="spin"/> : value==='done' ? <Check size={14}/> : <Circle size={12}/>} {value.replaceAll('_',' ')}</span>;}
const mascotArt = {laptop: mascot, walking, working, presenting, inspecting};
export function Mascot({className='', variant='laptop', alt=''}: {className?: string; variant?: keyof typeof mascotArt; alt?: string}) {return <img className={`mascot ${className}`} src={mascotArt[variant]} alt={alt}/>;}
// Mirrors CHARACTERS in src/reelhive/schemas/voice.py.
const CHARACTERS: Record<string, string> = {af_heart:'Heart · US female, warm',af_bella:'Bella · US female, bright and lively',af_nicole:'Nicole · US female, soft and close',am_michael:'Michael · US male, steady',am_fenrir:'Fenrir · US male, deep',am_puck:'Puck · US male, playful',bf_emma:'Emma · UK female, clear',bf_isabella:'Isabella · UK female, poised',bm_george:'George · UK male, classic',bm_fable:'Fable · UK male, a storyteller'};
type VoiceName = NonNullable<NonNullable<Brief['voice']>['name']>;

export function VoiceFields({value, onChange}: {value: NonNullable<Brief['voice']>; onChange: (v: NonNullable<Brief['voice']>)=>void}) {const named=!!value.name;return <div className="row"><Field label="Narrator"><select value={value.name||''} onChange={e=>{const name=(e.target.value||null) as VoiceName|null;onChange(name?{...value,name,accent:name[0]==='a'?'us':'uk',gender:name[1]==='f'?'female':'male'}:{...value,name:null});}}><option value="">By voice and accent</option>{Object.entries(CHARACTERS).map(([id,label])=><option key={id} value={id}>{label}</option>)}</select></Field><Field label="Voice"><select disabled={named} value={value.gender} onChange={e=>onChange({...value,gender:e.target.value as 'male'|'female'})}><option>female</option><option>male</option></select></Field><Field label="Accent"><select disabled={named} value={value.accent} onChange={e=>onChange({...value,accent:e.target.value as 'us'|'uk'})}><option value="us">US</option><option value="uk">UK</option></select></Field><Field label="Speed"><input type="number" min="0.8" max="1.2" step="0.05" value={value.speed} onChange={e=>onChange({...value,speed:+e.target.value})}/></Field></div>;}
