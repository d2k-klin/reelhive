import AxeBuilder from '@axe-core/playwright';
import {expect, test} from '@playwright/test';

const TOKEN = 'e2e-token';
const screens = [
  {path: '/', heading: /video/i},
  {path: '/runs', heading: /runs/i},
  {path: '/settings', heading: /settings/i},
];

test('the API refuses requests without the launch token or from another origin', async ({request}) => {
  expect((await request.get('/api/health')).status()).toBe(401);
  expect((await request.get(`/api/health?token=${TOKEN}`)).status()).toBe(200);
  const foreign = await request.post(`/api/briefs/validate?token=${TOKEN}`, {
    headers: {Origin: 'http://evil.example'},
    data: {},
  });
  expect(foreign.status()).toBe(403);
});

for (const theme of ['light', 'dark']) {
  test.describe(`${theme} theme`, () => {
    test.beforeEach(async ({page}) => {
      await page.addInitScript(value => localStorage.setItem('reelhive-theme', value), theme);
      await page.goto(`/?token=${TOKEN}`); // the token moves to sessionStorage and leaves the URL
      await expect(page).not.toHaveURL(/token=/);
    });

    for (const screen of screens) {
      test(`${screen.path} renders and passes axe (WCAG 2.1 A/AA)`, async ({page}) => {
        await page.goto(screen.path);
        await expect(page.getByRole('heading', {level: 1, name: screen.heading}).first()).toBeVisible();
        await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
        const results = await new AxeBuilder({page}).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
        const summary = results.violations.map(v => `${v.id} (${v.impact}): ${v.nodes.length} × ${v.nodes[0]?.target}`);
        expect(summary, summary.join('\n')).toEqual([]);
      });
    }
  });
}

test('keyboard users can reach the main navigation and skip to content', async ({page}) => {
  await page.goto(`/?token=${TOKEN}`);
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', {name: 'Skip to content'})).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.locator(':focus')).toBeVisible();
});
