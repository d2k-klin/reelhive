import type {components} from './schema';
export type Brief = components['schemas']['Brief'];
export type Run = components['schemas']['RunView'];
export type Script = components['schemas']['Script'];
export type Spec = components['schemas']['SceneSpec'];
export type Config = components['schemas']['Config'];
const launch = new URLSearchParams(location.search).get('token');
if (launch) { sessionStorage.setItem('reelhive-token', launch); history.replaceState(null, '', location.pathname); }
export const token = () => sessionStorage.getItem('reelhive-token') || '';
export const apiUrl = (path: string) => `/api${path}${path.includes('?') ? '&' : '?'}token=${encodeURIComponent(token())}`;
export class ApiError extends Error { constructor(public detail: unknown, public status: number) { super(typeof detail === 'string' ? detail : JSON.stringify(detail)); } }
export async function request<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const form = body instanceof FormData;
  const response = await fetch(`/api${path}`, {method, headers: {Authorization: `Bearer ${token()}`, ...(!form && body !== undefined ? {'Content-Type': 'application/json'} : {})}, body: body === undefined ? undefined : form ? body : JSON.stringify(body)});
  if (!response.ok) { const value = await response.json().catch(() => ({detail: response.statusText})); throw new ApiError(value.detail, response.status); }
  return response.headers.get('content-type')?.includes('application/json') ? response.json() : response.blob() as Promise<T>;
}
export function download(blob: Blob, name: string) { const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href=url; a.download=name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
export const fileUrl = (id: string, name: string) => apiUrl(`/runs/${id}/files/${name.split('/').map(encodeURIComponent).join('/')}`);
