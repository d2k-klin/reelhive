// @vitest-environment jsdom
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {MemoryRouter} from 'react-router-dom';
import {request, type Config} from '../api/client';
import {SettingsPage} from './Settings';

vi.mock('../api/client',()=>({request:vi.fn()}));

let config:Config;
beforeEach(()=>{
 localStorage.clear();vi.mocked(request).mockReset();
 config={provider:'claude',ollama_host:'http://localhost:11434',max_tokens:8000,runs_dir:'runs',models:{claude:{strong:'claude-strong',fast:'claude-fast'},copilot:{strong:'saved-model',fast:'auto'}},defaults:{level:'low',format:'16:9',voice:{gender:'female',accent:'us',speed:1},credit:'end'}};
 vi.mocked(request).mockImplementation(async(path,method,body)=>{
  if(path==='/settings')return method==='PUT'?body:config;
  if(path==='/providers/copilot/models')return ['claude-opus-5.5','other-model'];
  if(path==='/doctor')return [];
  return {};
 });
});
afterEach(cleanup);

function renderSettings(){
 const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
 render(<QueryClientProvider client={client}><MemoryRouter><SettingsPage/></MemoryRouter></QueryClientProvider>);
}

describe('Copilot model settings',()=>{
 it('only loads models when Copilot is selected and saves both tiers',async()=>{
  renderSettings();
  const strongProvider=await screen.findByLabelText('Strong tier');
  expect(screen.queryByLabelText('Copilot strong model')).toBeNull();
  expect(request).not.toHaveBeenCalledWith('/providers/copilot/models');
  fireEvent.change(strongProvider,{target:{value:'copilot'}});
  const strongModel=await screen.findByLabelText('Copilot strong model');
  await waitFor(()=>expect(strongModel.querySelector('option[value="claude-opus-5.5"]')).not.toBeNull());
  expect((strongModel as HTMLSelectElement).value).toBe('saved-model');
  fireEvent.change(strongModel,{target:{value:'claude-opus-5.5'}});
  fireEvent.change(screen.getByLabelText('Copilot fast model'),{target:{value:'other-model'}});
  fireEvent.click(screen.getByRole('button',{name:'Save settings'}));
  await waitFor(()=>expect(request).toHaveBeenCalledWith('/settings','PUT',expect.objectContaining({
   tier_providers:{strong:'copilot'},models:{claude:config.models!.claude,copilot:{strong:'claude-opus-5.5',fast:'other-model'}},
  })));
  fireEvent.change(screen.getByLabelText('Strong tier'),{target:{value:'claude'}});
  expect(screen.queryByLabelText('Copilot strong model')).toBeNull();
 });

 it('shows models for a Copilot agent override with automatic defaults',async()=>{
  config={...config,models:{},nodes:{music:'copilot'}};
  renderSettings();
  const strongModel=await screen.findByLabelText('Copilot strong model');
  expect((strongModel as HTMLSelectElement).value).toBe('auto');
  expect((screen.getByLabelText('Copilot fast model') as HTMLSelectElement).value).toBe('auto');
  await waitFor(()=>expect(request).toHaveBeenCalledWith('/providers/copilot/models'));
 });

 it('preserves configured models on discovery failure and supports refresh',async()=>{
  config={...config,provider:'copilot'};
  vi.mocked(request).mockImplementation(async(path)=>{
   if(path==='/settings')return config;
   if(path==='/providers/copilot/models')throw new Error('Copilot is not signed in');
   return path==='/doctor'?[]:{};
  });
  renderSettings();
  await screen.findByRole('alert');
  expect((screen.getByLabelText('Copilot strong model') as HTMLSelectElement).value).toBe('saved-model');
  fireEvent.click(screen.getByRole('button',{name:'Refresh models'}));
  await waitFor(()=>expect(vi.mocked(request).mock.calls.filter(([path])=>path==='/providers/copilot/models')).toHaveLength(2));
 });
});