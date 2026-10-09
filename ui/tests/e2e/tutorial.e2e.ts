import {expect, test} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.use({baseURL:'http://127.0.0.1:8798'});
const token='e2e-token';
const brief={level:'high',audience:'Product teams',storyline:'Make each scene clear',features:['Clear scenes'],duration:60,format:'16:9',voice:{gender:'female',accent:'us',speed:1},closing:'Tell your story',visuals:{source:'none'}};
test.beforeEach(async ({page})=>{
  await page.addInitScript(()=>localStorage.setItem('reelhive-quick-actions','off'));
  await page.goto(`/?token=${token}`);
});

test('field help works on hover, focus and tap, closes with Escape and never submits the form',async({page})=>{
  let writes=0;
  page.on('request',r=>{if(r.method()==='POST') writes++;});
  const help=page.getByRole('button',{name:'Help: Control level',exact:true});
  await help.hover();
  await expect(page.getByRole('tooltip')).toContainText('Small creates a video automatically');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('tooltip')).toBeHidden();
  await help.focus();
  await expect(page.getByRole('tooltip')).toBeVisible();
  await page.keyboard.press('Escape');
  await help.click();
  await expect(page.getByRole('tooltip')).toBeVisible();
  await page.mouse.wheel(0,120); // scrolling (as when a click scrolls the button into view) must not close it
  await expect(page.getByRole('tooltip')).toBeVisible();
  await page.getByRole('heading',{level:1}).click();
  await expect(page.getByRole('tooltip')).toBeHidden();
  expect(writes).toBe(0);
});

test('brief import, draft persistence, visual help and YAML export',async({page})=>{
  await page.getByLabel('Import brief file',{exact:true}).setInputFiles({name:'guide.yaml',mimeType:'application/yaml',buffer:Buffer.from(JSON.stringify(brief))});
  await expect(page.getByLabel('Who is this for?',{exact:true})).toHaveValue(brief.audience);
  await page.reload();
  await expect(page.getByLabel('Who is this for?',{exact:true})).toHaveValue(brief.audience);
  await expect(page.getByRole('button',{name:'Export brief file',exact:true})).toBeHidden(); // only once the brief is complete
  await page.getByRole('button',{name:'Continue to visuals',exact:true}).click();
  await page.getByLabel('Visual source',{exact:true}).selectOption('screenshots');
  await page.getByLabel('App URL',{exact:true}).fill('http://localhost:3000');
  await page.getByRole('button',{name:'Help: Mask selectors',exact:true}).click();
  await expect(page.getByRole('tooltip')).toContainText('black out');
  await page.keyboard.press('Escape');
  const downloaded=page.waitForEvent('download');
  await page.getByRole('button',{name:'Export brief file',exact:true}).click();
  expect((await downloaded).suggestedFilename()).toBe('brief.yaml');
});

test('sign-in completion uses the supported route',async({page})=>{
  // Avoid opening a real login browser; exercise the UI request contract and result handling.
  await page.route('**/api/login/start',r=>r.fulfill({json:{id:'tutorial-login'}}));
  let finished=false;
  await page.route('**/api/login/finish?id=tutorial-login',r=>{finished=true;return r.fulfill({json:{status:'signed_in'}});});
  await page.route('**/api/login/status?id=tutorial-login',r=>r.fulfill({json:{status:'signed_in',file:'/tmp/tutorial-auth.json'}}));
  await page.getByLabel('Import brief file',{exact:true}).setInputFiles({name:'brief.yaml',mimeType:'application/yaml',buffer:Buffer.from(JSON.stringify(brief))});
  await page.getByRole('button',{name:'Continue to visuals',exact:true}).click();
  await page.getByLabel('Visual source',{exact:true}).selectOption('screenshots');
  await page.getByLabel('App URL',{exact:true}).fill('http://localhost:3000');
  await page.getByRole('button',{name:'Sign in to your app',exact:true}).click();
  await page.getByRole('button',{name:'I finished signing in',exact:true}).click();
  await expect(page.getByRole('button',{name:'I finished signing in',exact:true})).toBeHidden();
  expect(finished).toBe(true);
});

test('scene edits persist through polling and must be saved before approval',async({page,request})=>{
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/runs/tutorial-scenes');
  const headline=page.getByLabel('Headline',{exact:true});
  await headline.fill('A clearer opening');
  await expect(page.getByRole('button',{name:'Approve all and render',exact:true})).toBeDisabled();
  await expect(page.getByRole('button',{name:'Regenerate scene',exact:true})).toBeDisabled();
  // Wait for a real poll, proving it cannot overwrite the user's local edit.
  await page.waitForResponse(r=>r.url().includes('/api/runs/tutorial-scenes')&&!r.url().includes('/events')&&r.request().method()==='GET');
  await expect(headline).toHaveValue('A clearer opening');
  await page.getByRole('button',{name:'Save scenes',exact:true}).click();
  await expect(page.getByRole('button',{name:'Save scenes',exact:true})).toBeDisabled({timeout:15000});
  await expect(page.getByText('Saved scenes are ready for approval.')).toBeVisible({timeout:15000});
  const saved=await(await request.get(`/api/runs/tutorial-scenes?token=${token}`)).json();
  expect(saved.spec.scenes[0].text.headline).toBe('A clearer opening');
  await page.reload();
  await expect(headline).toHaveValue('A clearer opening');
  await page.getByRole('button',{name:'Approve all and render',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Your video is ready.'})).toBeVisible({timeout:20000});
  expect(errors).toEqual([]);
});

test('script approval saves the visible narration',async({page,request})=>{
  await page.goto('/runs/tutorial-script');
  const narration=page.getByLabel('Narration 1',{exact:true});
  const original=await narration.inputValue();
  await narration.fill(original.replace('word','idea'));
  await expect(page.getByRole('button',{name:'Regenerate',exact:true})).toBeDisabled();
  await page.getByRole('button',{name:'Approve and continue',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Review the script'})).toBeHidden();
  const saved=await(await request.get(`/api/runs/tutorial-script?token=${token}`)).json();
  expect(saved.script.beats[0].narration).toBe(original.replace('word','idea'));
  await expect(page.getByRole('heading',{name:'Your video is ready.'})).toBeVisible({timeout:20000});
});

test('run library keyboard links, failure help, and completed downloads',async({page})=>{
  await page.goto('/runs');
  const runLink=page.locator('a[href="/runs/tutorial-failed"]');
  await runLink.focus();await page.keyboard.press('Enter');
  await expect(page.getByRole('complementary',{name:'Mr.D’s guide'})).toContainText('Production hit a problem');
  await expect(page.getByRole('button',{name:'Resume from checkpoint',exact:true})).toBeVisible();
  await page.goto('/runs/tutorial-done');
  const downloaded=page.waitForEvent('download');
  await page.getByRole('link',{name:'Run bundle',exact:true}).click();
  expect(await(await downloaded).failure()).toBeNull();
  await expect(page.locator('main')).not.toContainText(/Revideo|Kokoro|ffmpeg|React Flow|CopilotKit|gate\.result/);
});

for(const theme of ['light','dark']) for(const width of [390,1440]) {
  test(`tutorial, scenes, and settings are accessible at ${width}px in ${theme}`,async({page})=>{
    await page.setViewportSize({width,height:1000});
    await page.evaluate(value=>localStorage.setItem('reelhive-theme',value),theme);
    for(const path of ['/','/runs/tutorial-stopped','/settings']){
      await page.goto(path);
      await expect(page.getByRole('heading',{level:1})).toBeVisible();
      if(path==='/settings') await expect(page.getByLabel('Strong tier',{exact:true})).toBeVisible();
      if(path.includes('stopped')) await expect(page.getByLabel('Headline',{exact:true})).toBeVisible();
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),path).toBe(true);
      const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze();
      expect(axe.violations.map(v=>`${v.id}: ${v.nodes[0]?.target}`),path).toEqual([]);
    }
    await page.getByRole('button',{name:'Help: Strong tier',exact:true}).click();
    await expect(page.getByRole('tooltip')).toBeVisible();
    const box=await page.getByRole('tooltip').boundingBox();
    expect(box!.x+box!.width).toBeLessThanOrEqual(width);
  });
}

test('image approval must be saved and changing its request resets approval',async({page})=>{
  await page.goto('/runs/tutorial-images');
  const render=page.getByRole('button',{name:'Approve all and render',exact:true});
  const approval=page.getByRole('checkbox',{name:'Approve this image',exact:true});
  await expect(render).toBeDisabled();
  await approval.check();
  await expect(render).toBeDisabled();
  await page.getByRole('button',{name:'Save scenes',exact:true}).click();
  await expect(render).toBeEnabled({timeout:15000});
  await page.getByLabel('Visual kind',{exact:true}).selectOption('product_ui');
  await expect(approval).not.toBeChecked();
  await expect(page.getByLabel('Image or route',{exact:true})).toHaveValue('');
  await page.getByLabel('Image or route',{exact:true}).fill('/dashboard');
  await page.getByLabel('Visual kind',{exact:true}).selectOption('concept');
  await expect(page.getByLabel('Image or route',{exact:true})).toHaveValue('');
  await expect(render).toBeDisabled();
});

test('settings save persists defaults and per-agent inheritance',async({page})=>{
  await page.goto('/settings');
  await page.getByLabel('Control level',{exact:true}).selectOption('high');
  await page.getByRole('checkbox',{name:'Per-agent overrides',exact:true}).check();
  await page.getByLabel('Writing agent',{exact:true}).selectOption('openai');
  await page.getByRole('button',{name:'Save settings',exact:true}).click();
  await expect(page.getByText('Settings saved. Existing productions keep their original configuration.')).toBeVisible();
  await page.reload();
  await expect(page.getByLabel('Control level',{exact:true})).toHaveValue('high');
  await page.getByRole('checkbox',{name:'Per-agent overrides',exact:true}).check();
  await expect(page.getByLabel('Writing agent',{exact:true})).toHaveValue('openai');
  await page.getByLabel('Writing agent',{exact:true}).selectOption('');
  await page.getByRole('button',{name:'Save settings',exact:true}).click();
  await expect(page.getByText('Settings saved. Existing productions keep their original configuration.')).toBeVisible();
});
