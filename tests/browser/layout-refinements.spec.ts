import { test, expect } from '@playwright/test';

test('chapters keep their measure, photos fit, and the invitation never scales', async ({ page }, info) => {
  await page.route('**/api/session', route => route.fulfill({ status: 401, json: {} }));
  await page.goto('/');
  await expect(page.locator('.chapter-trigger')).toBeEnabled();
  await page.getByRole('button', { name: 'Italiano', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Italiano', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await page.evaluate(() => document.fonts.ready);
  await expect(page.locator('.envelope-prompt, a.skip')).toHaveCount(0);
  const envelope = (await page.locator('.envelope').boundingBox())!;
  const cue = (await page.locator('.skip-opening').boundingBox())!;
  expect(cue.y - (envelope.y + envelope.height)).toBeGreaterThan(24);
  await expect(page.locator('.envelope-paper')).toHaveCount(2);
  await expect(page.locator('.wax-seal svg')).toHaveCount(1);
  await expect(page.locator('.monogram svg')).toHaveCount(1);
  const hero = page.locator('.hero');
  const scene = page.locator('.envelope-scene');
  const original = (await hero.boundingBox())!;
  for (const progress of [0.32, 0.65, 0.85, 1]) {
    await scene.evaluate((el, p) => window.scrollTo({ top: (el as HTMLElement).offsetTop + (el.clientHeight - innerHeight) * p, behavior: 'instant' }), progress);
    await expect.poll(async () => (await hero.boundingBox())!.width).toBeCloseTo(original.width, 0);
    expect((await hero.boundingBox())!.height).toBeCloseTo(original.height, 0);
  }
  for (const section of ['#story', '#ceremony-visions']) {
    const target = page.locator(section);
    await target.scrollIntoViewIfNeeded();
    const boxes = await target.locator('figure').evaluateAll(els => els.map(el => {
      const { left, right } = el.getBoundingClientRect();
      return { left, right, viewport: innerWidth };
    }));
    for (const box of boxes) {
      expect(box.left).toBeGreaterThanOrEqual(0);
      expect(box.right).toBeLessThanOrEqual(box.viewport);
    }
    await target.screenshot({ path: info.outputPath(`${section.slice(1)}.png`) });
  }
  const heading = (await page.locator('.intro-copy').boundingBox())!;
  const firstChapter = (await page.locator('.story-chapter').first().boundingBox())!;
  expect(firstChapter.y).toBeGreaterThan(heading.y + heading.height);
  const titles = await page.locator('#story h2, #ceremony-visions h2, #memories h2').evaluateAll(els => els.map(el => getComputedStyle(el).fontSize));
  expect(new Set(titles).size).toBe(1);
  if (info.project.name === 'mobile') {
    const frames = page.locator('.dreams figure');
    const first = (await frames.nth(0).boundingBox())!;
    const second = (await frames.nth(1).boundingBox())!;
    expect(second.y).toBeGreaterThan(first.y + first.height);
    await page.setViewportSize({ width: 320, height: 740 });
    await expect.poll(() => page.evaluate(() => document.body.scrollWidth)).toBe(320);
  }
});
