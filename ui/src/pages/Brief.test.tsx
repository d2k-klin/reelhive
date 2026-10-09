// @vitest-environment jsdom
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {MemoryRouter} from 'react-router-dom';
import {BriefPage} from './Brief';

vi.mock('../api/client',()=>({
 request:vi.fn(async(path:string)=>path==='/music' ? [
  {file:'tech.mp3',mood:'tech',title:'Tech track'},
  {file:'calm.mp3',mood:'calm',title:'Calm track'},
 ] : path==='/settings' ? {defaults:{}} : {}),
 download:vi.fn(),fileUrl:vi.fn(),
}));

beforeEach(()=>{localStorage.clear();sessionStorage.clear();});
afterEach(cleanup);

describe('background music selection',()=>{
 it.each(['Low','Medium','High'])('allows music selection at %s customization',async(level)=>{
  const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
  render(<QueryClientProvider client={client}><MemoryRouter><BriefPage/></MemoryRouter></QueryClientProvider>);
  fireEvent.click(screen.getByRole('button',{name:new RegExp(`^${level}`)}));
  const track=screen.getByLabelText('Music track');
  await screen.findByRole('option',{name:'Calm track'});
  fireEvent.change(screen.getByLabelText('Music mood'),{target:{value:'calm'}});
  fireEvent.change(screen.getByLabelText('Music volume'),{target:{value:'0.5'}});
  fireEvent.change(track,{target:{value:'calm.mp3'}});
  expect((track as HTMLSelectElement).value).toBe('calm.mp3');
  expect(screen.getByLabelText('Calm track music sample').getAttribute('src')).toContain('/api/music/calm.mp3');
  await waitFor(()=>expect(JSON.parse(localStorage.getItem('reelhive-draft')||'{}')).toMatchObject({
   level:level.toLowerCase(),music_track:'calm.mp3',music_mood:'calm',music_volume:0.5,
  }));
  fireEvent.change(track,{target:{value:''}});
  expect((track as HTMLSelectElement).value).toBe('');
 });
});