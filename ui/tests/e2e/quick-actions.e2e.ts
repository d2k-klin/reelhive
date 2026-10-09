import AxeBuilder from '@axe-core/playwright';
import {expect, test} from '@playwright/test';

// M6 against the real server in --fake mode (see serve.py): CopilotKit + AG-UI, fake model, no API key.
const BASE = 'http://127.0.0.1:8798';
const TOKEN = 'e2e-token';
test.use({baseURL: BASE});

async function runWithStatus(request: any, status: string): Promise<string> {
  const runs = await (await request.get(`${BASE}/api/runs?token=${TOKEN}`)).json();
  const run = runs.find((r: any) => r.status === status && !r.id.startsWith('tutorial-'));
  expect(run, `a run in ${status}`).toBeTruthy();
  return run.id;
}

test('script quick actions: suggest, apply, undo, nothing leaves the machine', async ({page, request}) => {
  const outside: string[] = [];
  page.on('request', r => { if (!r.url().startsWith(BASE) && !r.url().startsWith('data:') && !r.url().startsWith('blob:')) outside.push(r.url()); });
  const id = await runWithStatus(request, 'awaiting_script');
  await page.goto(`/?token=${TOKEN}`);
  await page.goto(`/runs/${id}`);

  const chips = page.getByRole('group', {name: 'Suggestions for beat 1'});
  await expect(chips.locator('button.chip')).toHaveCount(3);
  await expect(page.getByText('Thinking of edits…')).toBeHidden();
  await expect(chips.getByRole('button', {name: /^Punchier hook/})).toHaveAttribute('title', /monthly cost number/);
  const before = await page.getByLabel('Narration 1').inputValue();

  await chips.getByRole('button', {name: /^Punchier hook/}).click();
  await expect(page.getByLabel('Narration 1')).not.toHaveValue(before, {timeout: 15_000});
  await expect(page.getByLabel('Narration 1')).toHaveValue(/rewritten/);

  await page.getByRole('button', {name: 'Undo last change', exact:true}).click();
  await expect(page.getByLabel('Narration 1')).toHaveValue(before, {timeout: 15_000});

  await expect.poll(async () => {
    const log = await (await request.get(`${BASE}/api/runs/${id}/files/run.log.jsonl?token=${TOKEN}`)).text();
    return ['"suggestion.offered"', '"suggestion.applied"', '"version.restored"'].every(event => log.includes(event));
  }).toBe(true);
  expect(outside, outside.join('\n')).toEqual([]);

  const results = await new AxeBuilder({page}).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
  expect(results.violations.map(v => `${v.id}: ${v.nodes[0]?.target}`)).toEqual([]);
});

test('scene quick actions: More ideas, apply, undo', async ({page, request}) => {
  const id = await runWithStatus(request, 'awaiting_scenes');
  await page.goto(`/?token=${TOKEN}`);
  await page.goto(`/runs/${id}`);
  const chips = page.getByRole('group', {name: 'Suggestions for scene 1'});
  await expect(chips.locator('button.chip')).toHaveCount(3);
  await page.getByRole('button', {name: 'More ideas', exact:true}).click();
  await expect(page.getByText('Thinking of edits…')).toBeHidden();
  await expect(chips.locator('button.chip')).toHaveCount(3);

  const errors: string[] = [];
  page.on('pageerror', e => errors.push(e.message));
  const headline = page.getByLabel('Headline', {exact:true});
  const before = await headline.inputValue();
  await headline.fill(before + '!'); // editing re-renders the live preview; it must not crash the page
  await page.waitForTimeout(800);
  await headline.fill(before);
  await chips.getByRole('button', {name: /^Shorten by ~2s/}).click();
  await expect(headline).toHaveValue('Cloud bills, explained', {timeout: 15_000});
  await page.getByRole('button', {name: 'Undo last change', exact:true}).click();
  await expect(headline).toHaveValue(before, {timeout: 15_000});
  expect(errors).toEqual([]);
});
