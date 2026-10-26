import { previewImage } from './media-fixtures';
import { test, expect } from './fixtures';

test('envelope grows, opens, releases the same invitation upward and reverses continuously', async ({ page }, info) => {
  await page.route('**/api/session', route => route.fulfill({ status: 401, json: { detail: 'Not authenticated' } }));
  await page.goto('/');
  await expect(page.locator('.chapter-trigger')).toBeEnabled();
  const scene = page.locator('.envelope-scene');
  const envelope = page.locator('.envelope');
  const initial = (await envelope.boundingBox())!;
  await expect(page.locator('.hero .invitation-link')).toHaveAttribute('inert', '');
  await page.screenshot({ path: info.outputPath('envelope-closed.png') });
  const scroll = async (p: number) => {
    await scene.evaluate((el, amount) => window.scrollTo({ top: (el as HTMLElement).offsetTop + (el.clientHeight - innerHeight) * amount, behavior: 'instant' }), p);
    await page.waitForTimeout(100);
  };
  await scroll(.32);
  expect((await envelope.boundingBox())!.width).toBeGreaterThan(initial.width);
  await scroll(.62);
  await expect.poll(async () => Number(await page.locator('.flap-layer').getAttribute('data-opening'))).toBeCloseTo(1, 5);
  await expect(page.locator('.top-edge')).toHaveAttribute('opacity', '0');
  await page.screenshot({ path: info.outputPath('envelope-open.png') });
  const before = (await page.locator('.letter-sheet').boundingBox())!;
  await scroll(.8);
  const midway = (await page.locator('.letter-sheet').boundingBox())!;
  expect(midway.y).toBeCloseTo(before.y, 0);
  expect(midway.width).toBeCloseTo(before.width, 0);
  expect(midway.height).toBeCloseTo(before.height, 0);
  await page.screenshot({ path: info.outputPath('invitation-emerging.png') });
  await scroll(1);
  await expect(scene).toHaveClass(/opened/);
  await expect(page.locator('.hero .invitation-link')).not.toHaveAttribute('inert');
  expect((await page.locator('.letter-sheet').boundingBox())!.y).toBeCloseTo(0, 0);
  await expect(page.locator('.hero')).toHaveCount(1);
  await page.screenshot({ path: info.outputPath('invitation-revealed.png') });
  await scroll(.8);
  expect((await page.locator('.letter-sheet').boundingBox())!.y).toBeCloseTo(midway.y, 0);
  await scroll(0);
  await page.getByRole('button', { name: 'Scroll to reveal' }).click();
  await expect(scene).toHaveClass(/opened/);
  expect(await page.evaluate(() => document.body.scrollWidth)).toBe(await page.evaluate(() => innerWidth));
});

test('private carousel waits for authentication and clears on logout', async ({ page }) => {
  let requests = 0;
  await page.route('**/api/session', route => route.fulfill({ status: route.request().method() === 'GET' ? 401 : 200, json: route.request().method() === 'POST' ? { id: 'guest', name: 'Guest', max_guests: 2, is_admin: false, is_witness: false, language: 'en' } : {} }));
  await page.route('**/api/photos/carousel', route => { requests++; return route.fulfill({ json: { items: [{ id: 'one', caption: 'A happy moment', preview: previewImage }] } }); });
  await page.goto('/');
  await expect(page.locator('.chapter-trigger')).toBeEnabled();
  expect(requests).toBe(0);
  await expect(page.locator('.carousel')).toHaveCount(0);
  await page.route('**/api/rsvp', route => route.fulfill({ json: { rsvp: null, prefill: { name: 'Guest', email: 'guest@example.test' } } }));
  await page.getByLabel('Your invitation code').fill('TEST-CODE');
  await page.getByRole('button', { name: 'Open my invitation' }).click();
  await expect(page.locator('.carousel')).toBeVisible();
  expect(requests).toBe(1);
  await page.getByRole('button', { name: 'Sign out', exact: true }).first().click();
  await expect(page.locator('.carousel')).toHaveCount(0);
  expect(requests).toBe(1);
  await page.getByLabel('Your invitation code').fill('TEST-CODE');
  await page.getByRole('button', { name: 'Open my invitation' }).click();
  await expect(page.locator('.carousel')).toBeVisible();
  expect(requests).toBe(2);

});

test('invitation email authenticates at the top; gallery email anchors uploads', async ({ page }) => {
  await page.route('**/api/session', route => route.fulfill({ json: { id: 'guest', name: 'Guest', max_guests: 2, is_admin: false, is_witness: false, language: 'en' } }));
  await page.route('**/api/rsvp', route => route.fulfill({ json: { rsvp: null, prefill: { name: 'Guest', email: 'guest@example.test' } } }));
  await page.route('**/api/photos**', route => route.fulfill({ json: { items: [], next: null } }));
  await page.goto('/#invite=TEST');
  await expect(page).toHaveURL(/\/$/);
  await expect.poll(() => page.evaluate(() => scrollY)).toBe(0);
  await page.goto('/gallery#invite=TEST');
  await expect(page).toHaveURL(/\/gallery#upload$/);
  await expect(page.locator('#upload')).toBeInViewport();
});


test('gallery loads immediately after code authentication', async ({ page }) => {
  let requests = 0;
  await page.route('**/api/session', route => route.fulfill({
    status: route.request().method() === 'GET' ? 401 : 200,
    json: { id: 'guest', name: 'Guest', max_guests: 2, is_admin: false, is_witness: false, language: 'en' }
  }));
  await page.route('**/api/photos', route => {
    requests++;
    return route.fulfill({ json: { items: [{ id: 'one', caption: 'A new memory', kind: 'photo', preview: previewImage, original: previewImage, motion: '' }], cursor: null } });
  });
  await page.goto('/gallery');
  await page.getByLabel('Your invitation code').fill('TEST-CODE');
  expect(requests).toBe(0);
  await page.getByRole('button', { name: 'Open my invitation' }).click();
  await expect(page.locator('.photo-card').filter({ hasText: 'A new memory' })).toBeVisible();
  expect(requests).toBe(1);
});
