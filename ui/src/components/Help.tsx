import {Children, isValidElement, useEffect, useId, useRef, useState, type ButtonHTMLAttributes, type ReactNode} from 'react';
import {createPortal} from 'react-dom';
import {CircleHelp} from 'lucide-react';
import {actionHelp} from './help-text';

export function Help({label, children}: {label: string; children: ReactNode}) {
  const id = useId();
  const anchor = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState({left: 0, top: 0});
  const show = () => {
    const rect = anchor.current?.getBoundingClientRect();
    if (rect) setPosition({left: Math.max(12, Math.min(rect.left, innerWidth - 312)), top: Math.min(rect.bottom + 8, innerHeight - 180)});
    setOpen(true);
  };
  useEffect(() => {
    if (!open) return;
    const key = (event: KeyboardEvent) => { if (event.key === 'Escape') setOpen(false); };
    const outside = (event: PointerEvent) => { if (!anchor.current?.contains(event.target as Node) && !panel.current?.contains(event.target as Node)) setOpen(false); };
    const close = () => setOpen(false);
    document.addEventListener('keydown', key);
    document.addEventListener('pointerdown', outside);
    window.addEventListener('scroll', close, true);
    window.addEventListener('resize', close);
    return () => { document.removeEventListener('keydown', key); document.removeEventListener('pointerdown', outside); window.removeEventListener('scroll', close, true); window.removeEventListener('resize', close); };
  }, [open]);
  return <><button ref={anchor} type="button" className="help-trigger" aria-label={`Help: ${label}`} aria-describedby={open ? id : undefined} aria-expanded={open} onMouseEnter={show} onFocus={show} onBlur={() => setOpen(false)} onClick={show}><CircleHelp size={16} aria-hidden/></button>{open && createPortal(<div ref={panel} id={id} role="tooltip" className="help-tooltip" style={position}>{children}</div>, document.body)}</>;
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
