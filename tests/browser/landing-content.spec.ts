import { test, expect } from '@playwright/test';

test('static content renders while the authenticated carousel request is pending, then scrolls approved previews', async ({ page }) => {
  let calls = 0;
  let release!: () => void;
  const pending = new Promise<void>(resolve => { release = resolve; });
  await page.route('**/api/photos/carousel', async route => {
    calls++;
    await pending;
    await route.fulfill({ json: { items: [{ id: 'one', caption: 'Our happy moment', preview: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="360" height="450"><rect width="360" height="450" fill="%239eaa98"/></svg>' }] } });
  });
  await page.route('**/api/session', route => route.fulfill({ json: { id: 'guest', name: 'Guest', max_guests: 2, is_admin: false, is_witness: false } }));
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#story')).toContainText('Zhavir and Saraerys.');
  await expect(page.locator('.story-keepsakes .polaroid')).toHaveCount(6);
  await expect(page.locator('.timeline-event')).toHaveCount(6);
  await expect(page.locator('.timeline-event').first()).toContainText('16:00');
  await expect(page.locator('#ceremony-visions')).toContainText('How we imagined the ceremony.');
  await expect.poll(() => calls).toBe(1);
  release();
  await expect(page.locator('.carousel')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Pause slideshow' })).toHaveCount(0);
  await expect(page.locator('.carousel .track')).toHaveCSS('animation-name', /drift$/);
  await page.getByRole('button', { name: 'Italiano', exact: true }).click();
  await expect(page.locator('#ceremony-visions')).toContainText('Come immaginavamo la cerimonia.');
  expect(calls).toBe(1);
  await expect(page.locator('a[href="https://youtu.be/uxnbkagUzrU?t=3"]')).toBeAttached();
  const slider = page.getByRole('slider');
  await slider.focus();
  await page.keyboard.press('ArrowRight');
  await expect(slider).toHaveValue('51');
});

test('carousel failure does not block landing content or the gallery link', async ({ page }) => {
  await page.route('**/api/photos/carousel', route => route.fulfill({ status: 503, json: { detail: 'Unavailable' } }));
  await page.goto('/');
  await expect(page.locator('#story')).toBeVisible();
  await expect(page.locator('#memories a.button')).toHaveAttribute('href', '/gallery#upload');
  await expect(page.locator('.carousel')).toHaveCount(0);
});

test('timeline is compact, highlights the current entry, and keeps petals inside their sections', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('.chapter-trigger')).toBeEnabled();
  await expect(page.locator('.envelope-scene .chapter-petal-layer')).toHaveCount(0);
  await expect(page.locator('#story')).toHaveCSS('position', 'relative');
  await expect(page.locator('#story')).toHaveCSS('isolation', 'isolate');
  await expect(page.locator('#story > .chapter-petal-layer')).toHaveCount(1);
  await expect(page.locator('#story > .intro-copy')).toHaveCSS('z-index', '1');
  await expect(page.locator('.event-keepsake')).toHaveCount(0);
  const events = page.locator('.timeline-event');
  const timelineBox = (await page.locator('.ribbon-timeline').boundingBox())!;
  for (let index = 0; index < 6; index++) {
    const box = (await events.nth(index).locator('.event-copy').boundingBox())!;
    if (index % 2) expect(box.x).toBeGreaterThan(timelineBox.x + timelineBox.width / 2);
    else expect(box.x + box.width).toBeLessThan(timelineBox.x + timelineBox.width / 2);
  }
  for (const index of [0, 2, 4, 5]) {
    await events.nth(index).evaluate(el => {
      const rect = el.getBoundingClientRect();
      window.scrollTo({ top: scrollY + rect.top + rect.height / 2 - innerHeight * .65, behavior: 'instant' });
    });
    await expect(events.nth(index)).toHaveAttribute('aria-current', 'step');
    await expect(page.locator('.timeline-event.active')).toHaveCount(1);
  }
  expect((await page.locator('.ribbon-timeline').boundingBox())!.height).toBeLessThan(1700);
  await page.getByRole('button', { name: 'Italiano', exact: true }).click();
  const rows = page.locator('.intro-copy h2 > *');
  const boxes = await rows.evaluateAll(elements => elements.map(el => ({ top: el.getBoundingClientRect().top, bottom: el.getBoundingClientRect().bottom })));
  expect(boxes[1].top).toBeGreaterThanOrEqual(boxes[0].bottom);
  expect(boxes).toHaveLength(2);
});
