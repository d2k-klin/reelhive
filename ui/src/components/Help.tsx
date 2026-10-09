import {Children, isValidElement, useEffect, useId, useLayoutEffect, useRef, useState, type ButtonHTMLAttributes, type ReactNode} from 'react';
import {createPortal} from 'react-dom';
import {CircleHelp} from 'lucide-react';
import {actionHelp} from './help-text';

/** A single, dismissible hint; tapping pins it, hovering never leaves a stray popup. */
export function Help({label, children}: {label: string; children: ReactNode}) {
  const id = useId();
  const anchor = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const pinned = useRef(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState({left:12,top:12});
  const clear = () => clearTimeout(timer.current);
  const close = () => { clear(); pinned.current=false; setOpen(false); };
  const place = () => {
    const rect = anchor.current?.getBoundingClientRect();
    if (!rect) return;
    const width=panel.current?.offsetWidth||300, height=panel.current?.offsetHeight||140;
    const below=rect.bottom+8;
    setPosition({left:Math.max(12,Math.min(rect.left,innerWidth-width-12)),top:Math.max(12,Math.min(below+height<=innerHeight-12?below:rect.top-height-8,innerHeight-height-12))});
  };
  const show = () => {
    clear();
    document.dispatchEvent(new CustomEvent('reelhive:help-open',{detail:id}));
    place(); setOpen(true);
  };
  const leave = () => {
    if (!pinned.current && document.activeElement!==anchor.current) timer.current=setTimeout(close,180);
  };
  useLayoutEffect(()=>{if(open)place();},[open,children]);
  useEffect(()=>{
    const other=(event:Event)=>{if((event as CustomEvent).detail!==id)close();};
    document.addEventListener('reelhive:help-open',other);
    return ()=>{clear();document.removeEventListener('reelhive:help-open',other);};
  },[id]);
  useEffect(()=>{
    if(!open)return;
    const key=(event:KeyboardEvent)=>{if(event.key==='Escape')close();};
    const outside=(event:PointerEvent)=>{if(!anchor.current?.contains(event.target as Node)&&!panel.current?.contains(event.target as Node))close();};
    const follow=()=>place();
    document.addEventListener('keydown',key);
    document.addEventListener('pointerdown',outside);
    window.addEventListener('scroll',follow,true);
    window.addEventListener('resize',follow);
    return ()=>{document.removeEventListener('keydown',key);document.removeEventListener('pointerdown',outside);window.removeEventListener('scroll',follow,true);window.removeEventListener('resize',follow);};
  },[open]);
  return <><button ref={anchor} type="button" className="help-trigger" aria-label={`Help: ${label}`} aria-describedby={open?id:undefined} aria-expanded={open}
    onMouseEnter={show} onMouseLeave={leave} onFocus={show} onBlur={close}
    onClick={()=>{if(pinned.current)close();else{pinned.current=true;show();}}}><CircleHelp size={15} aria-hidden/></button>
    {open&&createPortal(<div ref={panel} id={id} role="tooltip" className="help-tooltip" style={position} onMouseEnter={clear} onMouseLeave={leave}><strong>{label}</strong><span>{children}</span></div>,document.body)}</>;
}

function textContent(children: ReactNode): string {
  return Children.toArray(children).map(child => typeof child === 'string' || typeof child === 'number' ? String(child) : isValidElement<{children?: ReactNode}>(child) ? textContent(child.props.children) : '').join('').trim();
}

/** Keep help beside disabled actions too, so their consequences remain discoverable. */
export function Button({help, children, ...props}: ButtonHTMLAttributes<HTMLButtonElement> & {help?: string}) {
  const label = props['aria-label'] || textContent(children);
  const explanation = help || actionHelp(label);
  const control = <button type="button" {...props}>{children}</button>;
  return explanation ? <span className={`action-help ${props.className === 'icon' || props.className?.includes('icon ') ? 'icon-help' : ''}`}>{control}<Help label={label}>{explanation}</Help></span> : control;
}
