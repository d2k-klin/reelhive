// @vitest-environment jsdom
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {request} from '../api/client';
import {PublishPanel} from './Publish';

vi.mock('../api/client',()=>({request:vi.fn()}));

const job={platforms:['youtube'],status:'awaiting_approval',failures:[],warnings:['TikTok is vertical'],results:{},
 posts:{youtube:{title:'CostHive in 60 seconds',description:'Find waste.',tags:['finops']}}};

beforeEach(()=>{
 vi.mocked(request).mockReset();
 vi.mocked(request).mockImplementation(async(path)=>{
  if(path==='/runs/r1/publish')return job;
  if(path==='/publish/accounts')return [{platform:'youtube',title:'YouTube',configured:true,env:[],setup:'',redirect_uri:'',account:{name:'me',expires_at:null}}];
  return {ok:true};
 });
});
afterEach(cleanup);

function renderPanel(){
 const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
 return render(<QueryClientProvider client={client}><PublishPanel runId="r1"/></QueryClientProvider>);
}

describe('Publish panel',()=>{
 it('shows the drafted copy and posts only after an explicit confirmation',async()=>{
  renderPanel();
  const title=await screen.findByDisplayValue('CostHive in 60 seconds');
  expect(screen.getByText('TikTok is vertical')).toBeTruthy();
  fireEvent.change(title,{target:{value:'CostHive, explained'}});
  fireEvent.click(screen.getByRole('button',{name:'Publish…'}));
  expect(vi.mocked(request).mock.calls.filter(([path,method])=>path==='/runs/r1/publish'&&method==='POST')).toHaveLength(0);
  expect(screen.getByRole('alertdialog',{name:'Confirm publishing'})).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Yes, publish'}));
  await waitFor(()=>expect(request).toHaveBeenCalledWith('/runs/r1/publish','POST',{confirm:true}));
  expect(request).toHaveBeenCalledWith('/runs/r1/publish/posts','PUT',expect.objectContaining({youtube:expect.objectContaining({title:'CostHive, explained'})}));
 });

 it('cancelling the confirmation posts nothing',async()=>{
  renderPanel();
  await screen.findByDisplayValue('CostHive in 60 seconds');
  fireEvent.click(screen.getByRole('button',{name:'Publish…'}));
  fireEvent.click(screen.getByRole('button',{name:'Cancel'}));
  expect(vi.mocked(request).mock.calls.filter(([path,method])=>path==='/runs/r1/publish'&&method==='POST')).toHaveLength(0);
 });
});
