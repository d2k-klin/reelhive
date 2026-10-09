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
  const help=page.getByRole('button',{name:'Help: Customization level',exact:true});
  await help.hover();
  await expect(page.getByRole('tooltip')).toContainText('Low: the agents research');
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

test('auto visuals inherit the website for capture, export and production, with an optional override',async({page})=>{
  const captures: {url:string;routes:string[]}[]=[];
  let exported:any, started:any;
  await page.route('**/api/capture/test',r=>{
    captures.push(r.request().postDataJSON().screenshots);
    return r.fulfill({json:[]});
  });
  await page.route('**/api/briefs/export',r=>{exported=r.request().postDataJSON();return r.continue();});
  await page.route('**/api/runs/*/start',r=>{started=r.request().postDataJSON();return r.fulfill({json:{status:'producing'}});});
  await page.getByLabel('Who is this for?',{exact:true}).fill('Product teams');
  await page.getByLabel('What’s the story?',{exact:true}).fill('Show our product in action');
  await page.getByLabel('Feature 1',{exact:true}).fill('Clear dashboard');
  await page.getByLabel('Closing idea',{exact:true}).fill('Try the product');
  await page.getByLabel('Product website',{exact:true}).fill('https://product.example');
  await page.getByLabel('Visual source',{exact:true}).selectOption('auto');
  await expect(page.getByLabel('App URL',{exact:true})).toBeHidden();
  await expect(page.getByText('Screenshots use your product website:')).toContainText('https://product.example');
  await page.getByLabel('Routes',{exact:true}).fill('/dashboard');
  await page.getByRole('button',{name:'Test capture',exact:true}).click();
  await expect.poll(()=>captures.length).toBe(1);
  expect(captures[0]).toMatchObject({url:'https://product.example',routes:['/dashboard']});
  await page.locator('section').filter({has:page.getByRole('heading',{name:'Your visuals',exact:true})})
    .screenshot({path:'/private/tmp/reelhive-auto-visuals.png'});

  await page.getByRole('button',{name:'Use another app URL',exact:true}).click();
  await page.getByLabel('App URL',{exact:true}).fill('https://app.example');
  await page.reload();
  await expect(page.getByLabel('App URL',{exact:true})).toHaveValue('https://app.example');
  await page.getByRole('button',{name:'Test capture',exact:true}).click();
  await expect.poll(()=>captures.length).toBe(2);
  expect(captures[1].url).toBe('https://app.example');
  await page.getByRole('button',{name:'Use product website',exact:true}).click();
  await page.getByLabel('Product website',{exact:true}).fill('https://new-product.example');
  await expect(page.getByLabel('App URL',{exact:true})).toBeHidden();
  const downloaded=page.waitForEvent('download');
  await page.getByRole('button',{name:'Export brief file',exact:true}).click();
  await downloaded;
  expect(exported.visuals.screenshots).toMatchObject({url:'https://new-product.example',routes:['/dashboard']});
  await page.getByRole('button',{name:'Make my video',exact:true}).click();
  await expect.poll(()=>started?.visuals?.screenshots?.url).toBe('https://new-product.example');
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
  await page.getByRole('link',{name:'Download all files (.zip)',exact:true}).click();
  expect(await(await downloaded).failure()).toBeNull();
  await expect(page.locator('main')).not.toContainText(/Revideo|Kokoro|ffmpeg|React Flow|CopilotKit|gate\.result/);
});

for(const theme of ['light','dark']) for(const width of [390,1440]) {
  test(`tutorial, scenes, and settings are accessible at ${width}px in ${theme}`,async({page})=>{
    await page.setViewportSize({width,height:1000});
    await page.evaluate(value=>localStorage.setItem('reelhive-theme',value),theme);
    for(const path of ['/','/runs','/runs/tutorial-stopped','/settings']){
      await page.goto(path);
      await expect(page.getByRole('heading',{level:1})).toBeVisible();
      if(path==='/') await page.getByRole('button',{name:'High You direct every scene',exact:true}).click();
      if(path==='/settings') {
        await expect(page.getByLabel('Strong tier',{exact:true})).toBeVisible();
        await page.getByRole('checkbox',{name:'Per-agent overrides',exact:true}).check();
      }
      if(path.includes('stopped')) {
        await expect(page.getByLabel('Headline',{exact:true})).toBeVisible();
        await page.getByRole('checkbox',{name:'Override voice',exact:true}).check();
      }
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),path).toBe(true);
      const geometry=await page.evaluate(()=>{
        const rects=(selector:string)=>Array.from(document.querySelectorAll<HTMLElement>(selector))
          .filter(el=>el.getClientRects().length&&el.getBoundingClientRect().width>0)
          .map(el=>el.getBoundingClientRect());
        const controls=rects('main .field input:not([type=checkbox]):not([type=file]), main select, main .filters input');
        const crowdedFeatures=Array.from(document.querySelectorAll('.feature-row')).filter(row=>{
          const boxes=Array.from(row.querySelectorAll<HTMLElement>('input,.action-help')).map(el=>el.getBoundingClientRect());
          return boxes.some((box,i)=>i>0&&box.left<boxes[i-1].right-1);
        }).length;
        const misalignedRows=Array.from(document.querySelectorAll('.row')).filter(row=>{
          const fields=Array.from(row.children).filter(el=>el.matches('.field'));
          return fields.some((field,i)=>fields.slice(i+1).some(other=>{
            const a=field.querySelector(':scope > input,:scope > select');
            const b=other.querySelector(':scope > input,:scope > select');
            return a&&b&&Math.abs(field.getBoundingClientRect().top-other.getBoundingClientRect().top)<1
              &&Math.abs(a.getBoundingClientRect().top-b.getBoundingClientRect().top)>1;
          }));
        }).map(row=>Array.from(row.querySelectorAll(':scope > .field .field-heading')).map(heading=>heading.textContent));
        return {heights:Array.from(new Set(controls.map(r=>Math.round(r.height)))),crowdedFeatures,misalignedRows};
      });
      expect(geometry.heights.length,`${path}: inconsistent control heights ${geometry.heights}`).toBeLessThanOrEqual(1);
      expect(geometry.crowdedFeatures,`${path}: overlapping feature actions`).toBe(0);
      expect(geometry.misalignedRows,`${path}: uneven controls in the same row`).toEqual([]);
      const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze();
      expect(axe.violations.map(v=>`${v.id}: ${v.nodes[0]?.target}`),path).toEqual([]);
      if(theme==='dark'&&width===1440){
        const anchor=path==='/'?page.getByLabel('Voice',{exact:true}):path==='/settings'?page.getByLabel('Credit placement',{exact:true}):path==='/runs'?page.getByLabel('Filter by status',{exact:true}):page.getByLabel('Headline',{exact:true});
        await anchor.scrollIntoViewIfNeeded();
        await page.screenshot({path:`/private/tmp/reelhive-aligned-${path==='/'?'brief':path==='/settings'?'settings':path==='/runs'?'runs':'scenes'}.png`});
      }
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
  await page.getByLabel('Customization level',{exact:true}).selectOption('high');
  await page.getByRole('checkbox',{name:'Per-agent overrides',exact:true}).check();
  await page.getByLabel('Writing agent',{exact:true}).selectOption('openai');
  await page.getByRole('button',{name:'Save settings',exact:true}).click();
  await expect(page.getByText('Settings saved. Existing productions keep their original configuration.')).toBeVisible();
  await page.reload();
  await expect(page.getByLabel('Customization level',{exact:true})).toHaveValue('high');
  await page.getByRole('checkbox',{name:'Per-agent overrides',exact:true}).check();
  await expect(page.getByLabel('Writing agent',{exact:true})).toHaveValue('openai');
  await page.getByLabel('Writing agent',{exact:true}).selectOption('');
  await page.getByRole('button',{name:'Save settings',exact:true}).click();
  await expect(page.getByText('Settings saved. Existing productions keep their original configuration.')).toBeVisible();
});

test('clear form starts a new brief and the notes-first fields are there',async({page})=>{
  await page.getByLabel('Who is this for?',{exact:true}).fill('Users of scancomb.com');
  await page.getByLabel('Product website',{exact:true}).fill('https://scancomb.com');
  await expect(page.getByLabel('Closing idea',{exact:true})).toBeVisible();
  await expect(page.locator('.sample-frame')).toContainText('scancomb.com');
  await expect(page.locator('.sample-frame')).not.toContainText(brief.features[0]); // notes are never shown as headlines
  page.once('dialog',dialog=>dialog.accept());
  await page.getByRole('button',{name:'Clear form',exact:true}).click();
  await expect(page.getByLabel('Who is this for?',{exact:true})).toHaveValue('');
  await expect(page.getByLabel('Product website',{exact:true})).toHaveValue('');
  await page.reload();
  await expect(page.getByLabel('Who is this for?',{exact:true})).toHaveValue('');
});

test('duration slider and seconds stay synchronized through pointer, keyboard, and reload',async({page})=>{
  const slider=page.getByRole('slider',{name:/Duration/});
  const seconds=page.getByLabel('Seconds',{exact:true});
  await slider.scrollIntoViewIfNeeded();
  const box=(await slider.boundingBox())!;
  await page.mouse.click(box.x+box.width*.72,box.y+box.height/2);
  const dragged=await slider.inputValue();
  expect(Number(dragged)).toBeGreaterThan(100);
  await expect(seconds).toHaveValue(dragged);
  await slider.focus();await page.keyboard.press('ArrowRight');
  await expect(seconds).toHaveValue(String(Number(dragged)+1));
  await seconds.fill('90');
  await expect(slider).toHaveValue('90');
  await page.reload();
  await expect(slider).toHaveValue('90');
  await expect(seconds).toHaveValue('90');
});

test('help cleans up after hover and keeps only one pinned hint',async({page})=>{
  const first=page.getByRole('button',{name:'Help: Customization level',exact:true});
  await first.hover();
  await expect(page.getByRole('tooltip')).toBeVisible();
  await page.getByRole('heading',{level:1}).hover();
  await expect(page.getByRole('tooltip')).toBeHidden();
  await first.click();
  await page.getByRole('heading',{level:1}).hover();
  await expect(page.getByRole('tooltip')).toBeVisible();
  await page.getByRole('button',{name:'Help: Who is this for?',exact:true}).hover();
  await expect(page.getByRole('tooltip')).toHaveCount(1);
  await expect(page.getByRole('tooltip')).toContainText('Name the audience');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('tooltip')).toBeHidden();
});

for(const width of [390,1440]) test(`production path and long briefs stay readable at ${width}px`,async({page})=>{
  await page.setViewportSize({width,height:1000});
  const story='I want a promotion video about what is offered, the features and services, why we built the product, and why compliance matters in the era of AI. '.repeat(3);
  await page.route('**/api/runs/tutorial-failed',async route=>{
    const response=await route.fetch();const data=await response.json();
    await route.fulfill({json:{...data,brief:{...data.brief,storyline:story}}});
  });
  await page.goto('/runs/tutorial-failed');
  const title=page.getByRole('heading',{level:1});
  await expect(title).toBeVisible();
  expect(await title.evaluate(el=>parseFloat(getComputedStyle(el).fontSize))).toBeLessThanOrEqual(32);
  expect((await title.textContent())!.length).toBeLessThanOrEqual(140); // trimmed, never the entire brief as a hero
  await page.getByText('Read full story brief',{exact:true}).click();
  await expect(page.locator('.full-brief p')).toHaveText(story.trim());
  const path=page.getByRole('region',{name:'Production progress',exact:true});
  await expect(path.getByRole('heading',{level:3})).toHaveCount(5);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze();
  expect(axe.violations.map(v=>`${v.id}: ${v.nodes[0]?.target}`)).toEqual([]);
});

for(const level of ['low','medium']) test(`${level} recovery continues without individual image approval`,async({page,request})=>{
  const id=`tutorial-${level}-images`;
  await page.goto(`/runs/${id}`);
  await expect(page.getByLabel('Headline',{exact:true})).toBeVisible();
  await expect(page.getByRole('checkbox',{name:'Approve this image',exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Help: Approve this image',exact:true})).toHaveCount(0);
  await expect(page.locator('.timeline i')).toHaveCount(0);
  const saved=await(await request.get(`/api/runs/${id}?token=${token}`)).json();
  expect(saved.spec.scenes[0].visual).toBeTruthy();
  expect(saved.spec.scenes[0].image_approved).toBe(false);
  const resume=page.getByRole('button',{name:'Continue production',exact:true});
  await expect(resume).toBeEnabled();
  await resume.click();
  await expect(page.getByRole('heading',{name:'Your video is ready.'})).toBeVisible({timeout:20000});
});
