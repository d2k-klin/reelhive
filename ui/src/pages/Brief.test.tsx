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
describe('brief progressive disclosure',()=>{
 function renderBrief() {
  const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
  return render(<QueryClientProvider client={client}><MemoryRouter><BriefPage/></MemoryRouter></QueryClientProvider>);
 }
 it('shows voice controls for narration or captions and retains the chosen voice',async()=>{
  renderBrief();
  await screen.findByRole('option',{name:'Calm track'});
  fireEvent.change(screen.getByLabelText('Voice'),{target:{value:'male'}});
  fireEvent.click(screen.getByRole('checkbox',{name:'Narrator voice'}));
  expect(screen.queryByLabelText('Voice')).toBeNull();
  fireEvent.click(screen.getByRole('checkbox',{name:'Captions'}));
  expect((screen.getByLabelText('Voice') as HTMLSelectElement).value).toBe('male');
  expect(screen.getByText('Voice timing is used to synchronize your captions.')).toBeTruthy();
  fireEvent.click(screen.getByRole('checkbox',{name:'Captions'}));
  fireEvent.click(screen.getByRole('checkbox',{name:'Narrator voice'}));
  expect((screen.getByLabelText('Voice') as HTMLSelectElement).value).toBe('male');
 });
 it('hides music controls when disabled without clearing their values',async()=>{
  renderBrief();
  await screen.findByRole('option',{name:'Calm track'});
  fireEvent.change(screen.getByLabelText('Music track'),{target:{value:'calm.mp3'}});
  fireEvent.click(screen.getByRole('checkbox',{name:'Background music'}));
  expect(screen.queryByLabelText('Music track')).toBeNull();
  fireEvent.click(screen.getByRole('checkbox',{name:'Background music'}));
  expect((screen.getByLabelText('Music track') as HTMLSelectElement).value).toBe('calm.mp3');
 });
 it('starts optional details collapsed and opens screenshots when a website is supplied',async()=>{
  const {container}=renderBrief();
  await screen.findByRole('option',{name:'Calm track'});
  const details=Array.from(container.querySelectorAll('details'));
  expect(details.every(d=>!d.open)).toBe(true);
  fireEvent.change(screen.getByLabelText('Product website'),{target:{value:'https://example.com'}});
  expect(screen.getByText('App screenshots',{selector:'strong'}).closest('details')?.open).toBe(true);
  expect(screen.getByText('Capture settings').closest('details')?.open).toBe(false);
  fireEvent.change(screen.getByLabelText('Product website'),{target:{value:''}});
  expect(screen.getByText('App screenshots',{selector:'strong'}).closest('details')?.open).toBe(true);
 });
 it('retains image and capture customizations when switching visual sources',async()=>{
  renderBrief();
  await screen.findByRole('option',{name:'Calm track'});
  const source=screen.getByLabelText('Visual source');
  fireEvent.change(source,{target:{value:'images'}});
  fireEvent.change(screen.getByLabelText('Or use a local image folder'),{target:{value:'/tmp/my-images'}});
  fireEvent.change(source,{target:{value:'screenshots'}});
  fireEvent.change(screen.getByLabelText('App URL'),{target:{value:'https://example.com/app'}});
  fireEvent.change(source,{target:{value:'images'}});
  expect((screen.getByLabelText('Or use a local image folder') as HTMLInputElement).value).toBe('/tmp/my-images');
  fireEvent.change(source,{target:{value:'screenshots'}});
  expect((screen.getByLabelText('App URL') as HTMLInputElement).value).toBe('https://example.com/app');
 });
 it('reveals brand colors with the brand theme and keeps logo upload available',async()=>{
  renderBrief();
  await screen.findByRole('option',{name:'Calm track'});
  fireEvent.click(screen.getByRole('button',{name:/^High/}));
  expect(screen.queryByLabelText('Accent',{selector:'input[type=color]'})).toBeNull();
  expect(screen.getByLabelText('Upload logo')).toBeTruthy();
  fireEvent.change(screen.getByLabelText('Theme'),{target:{value:'brand'}});
  fireEvent.change(screen.getByLabelText('Accent',{selector:'input[type=color]'}),{target:{value:'#ff8800'}});
  fireEvent.change(screen.getByLabelText('Theme'),{target:{value:'default'}});
  expect(screen.queryByLabelText('Accent',{selector:'input[type=color]'})).toBeNull();
  fireEvent.change(screen.getByLabelText('Theme'),{target:{value:'brand'}});
  expect((screen.getByLabelText('Accent',{selector:'input[type=color]'}) as HTMLInputElement).value).toBe('#ff8800');
 });
});
