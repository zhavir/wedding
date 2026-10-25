import { test, expect } from '@playwright/test';

test('invitation opens, chapter links skip ahead, and the footer ties again', async ({ page }, testInfo) => {
  await page.goto('/');
  await expect(page.locator('.chapter-trigger')).toBeEnabled();
  const opening = page.locator('.envelope-scene');
  await expect(page.locator('.skip-opening')).toBeInViewport();
  await expect(page.getByRole('button', { name: 'Scroll to reveal' })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('invitation-closed.png') });
  await page.getByRole('button', { name: 'Scroll to reveal' }).click();
  await expect.poll(() => opening.evaluate(el => Number(getComputedStyle(el).getPropertyValue('--page-reveal')))).toBeGreaterThan(.9);
  const picker = page.locator('.chapter-trigger');
  const chapters = page.getByRole('navigation', { name: 'Jump to a chapter' });
  await picker.click();
  await expect(chapters.getByRole('link')).toHaveCount(7);
  await chapters.getByRole('link', { name: /Getting there/ }).click();
  await expect(page).toHaveURL(/#travel$/);
  await picker.click();
  await chapters.getByRole('link', { name: /The day/ }).click();
  await expect(page).toHaveURL(/#details$/);
  const timeline = page.locator('.ribbon-timeline');
  await timeline.scrollIntoViewIfNeeded();
  const start = await page.locator('.thread-progress').getAttribute('stroke-dashoffset');
  await page.locator('.timeline-event').last().scrollIntoViewIfNeeded();
  await expect.poll(async () => Number(await page.locator('.thread-progress').getAttribute('stroke-dashoffset'))).toBeLessThan(Number(start));
  await expect(page.locator('.timeline-event.arrived').first()).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('timeline.png') });
  await picker.click();
  await chapters.getByRole('link', { name: 'RSVP' }).click();
  await expect(page).toHaveURL(/#rsvp$/);
  await expect(page.locator('#rsvp')).toBeInViewport();
  await page.locator('footer').scrollIntoViewIfNeeded();
  await expect(page.locator('footer')).toHaveClass('tied');
  await page.screenshot({ path: testInfo.outputPath('footer.png') });
  expect(await page.evaluate(() => document.body.scrollWidth)).toBe(await page.evaluate(() => innerWidth));
});

test('reduced motion exposes the invitation and timeline without an entrance gate', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  await expect(page.locator('.chapter-trigger')).toBeEnabled();
  await expect(page.locator('.hero-monogram, .obsolete-seal')).toHaveCount(0);
  await expect(page.locator('.skip-opening')).toBeHidden();
  await expect(page.locator('.envelope').first()).toBeHidden();
  await expect(page.locator('.hero h1')).toBeVisible();
  await page.locator('.ribbon-timeline').scrollIntoViewIfNeeded();
  await expect(page.locator('.thread-progress')).toHaveAttribute('stroke-dashoffset', '0');
  await expect(page.locator('.timeline-bead')).toBeHidden();
});


test('ceremony dreams, botanical borders and chapter picker are available in both languages', async ({ page }, testInfo) => {
  await page.goto('/');
  await expect(page.locator('.chapter-trigger')).toBeEnabled();
  await expect(page.locator('.chapter-petal-layer').first()).toBeVisible();
  const picker = page.locator('.chapter-trigger');
  await picker.click();
  await page.getByRole('navigation', { name: 'Jump to a chapter' }).getByRole('link', { name: /Our ceremony dreams/ }).click();
  await expect(page).toHaveURL(/#ceremony-visions$/);
  await expect(page.locator('#ceremony-visions')).toContainText('How we imagined the ceremony.');
  await page.getByRole('button', { name: 'Italiano', exact: true }).click();
  await expect(page.locator('#ceremony-visions')).toContainText('Come immaginavamo la cerimonia.');
  await page.locator('#ceremony-visions').scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath('ceremony-italian.png') });
  await picker.click();
  await page.keyboard.press('Escape');
  await expect(picker).toHaveAttribute('aria-expanded', 'false');
  await expect(picker).toBeFocused();
});


test('chapter dock expands without rotating labels and gallery shares the masthead', async ({ page }, testInfo) => {
  await page.goto('/');
  await expect(page.locator('.chapter-trigger')).toBeEnabled();
  const header = page.locator('.site-header');
  const homeHeader = await header.boundingBox();
  const dock = page.locator('.chapter-picker');
  const trigger = page.getByRole('button', { name: 'Explore the chapters' });
  const closed = await dock.boundingBox();
  await trigger.click();
  await expect(trigger).toHaveAttribute('aria-expanded', 'true');
  await expect(page.locator('.chapter-panel')).toBeVisible();
  await expect.poll(async () => {
    const panel = await page.locator('.chapter-panel').boundingBox();
    return panel!.x + panel!.width;
  }).toBeLessThan(closed!.x);
  const expanded = await dock.boundingBox();
  expect(Math.abs(expanded!.y + expanded!.height - closed!.y - closed!.height)).toBeLessThan(2);
  await page.screenshot({ path: testInfo.outputPath('chapters-expanded.png') });
  await page.keyboard.press('Escape');
  await expect(trigger).toHaveAttribute('aria-expanded', 'false');
  await page.goto('/gallery');
  await expect(page.locator('.site-header.gallery-header')).toBeVisible();
  await expect(page.getByRole('link', { name: '← Back to our wedding' })).toBeVisible();
  const galleryHeader = await page.locator('.site-header').boundingBox();
  const title = await page.locator('.gallery-title').boundingBox();
  expect(galleryHeader!.y).toBeCloseTo(homeHeader!.y, 0);
  expect(galleryHeader!.y + galleryHeader!.height).toBeLessThan(title!.y);
  await page.screenshot({ path: testInfo.outputPath('gallery-header.png') });
  await page.locator('footer').scrollIntoViewIfNeeded();
  expect(await page.locator('.marquee-group').first().evaluate(el => el.getBoundingClientRect().width)).toBeGreaterThanOrEqual(await page.evaluate(() => innerWidth));
  expect(await page.evaluate(() => document.body.scrollWidth)).toBe(await page.evaluate(() => innerWidth));
});

test('timeline ink tracks its marker and Akamaru reveals his namesake', async ({ page }, testInfo) => {
  await page.goto('/');
  await expect(page.locator('.chapter-trigger')).toBeEnabled();
  await expect(page.locator('.chapter-trigger')).toBeEnabled();
  const timeline = page.locator('.ribbon-timeline');
  for (const fraction of [.25, .6, 1]) {
    await timeline.evaluate((el, fraction) => {
      const rect = el.getBoundingClientRect();
      window.scrollTo({top: scrollY + rect.top + rect.height * fraction - innerHeight * .65, behavior: 'instant'});
    }, fraction);
    await page.waitForTimeout(100);
    const geometry = await page.locator('.thread-progress').evaluate((el: SVGPathElement) => {
      const offset = Number(el.getAttribute('stroke-dashoffset'));
      const matrix = el.getScreenCTM()!;
      const point = el.getPointAtLength(el.getTotalLength() * (1 - offset)).matrixTransform(matrix);
      const bead = document.querySelector('.timeline-bead')!.getBoundingClientRect();
      return {offset, sx: matrix.a, sy: matrix.d, gap: Math.hypot(point.x - bead.x - bead.width / 2, point.y - bead.y - bead.height / 2)};
    });
    expect(geometry.sx).toBeCloseTo(1, 2);
    expect(geometry.sy).toBeCloseTo(1, 2);
    expect(geometry.gap).toBeLessThan(1);
    if (fraction === 1) expect(geometry.offset).toBeLessThan(.001);
  }
  await page.screenshot({path: testInfo.outputPath('timeline-end.png')});
  const slider = page.getByRole('slider');
  await slider.focus();
  await page.keyboard.press('End');
  await expect(slider).toHaveValue('100');
  await page.keyboard.press('Home');
  await expect(slider).toHaveValue('0');

});

test('save the date downloads the confirmed wedding event in both languages', async ({ page }) => {
  await page.emulateMedia({reducedMotion: 'reduce'});
  await page.goto('/');
  await expect(page.locator('.chapter-trigger')).toBeEnabled();
  for (const language of ['English', 'Italiano']) {
    await page.getByRole('button', {name: language, exact: true}).click();
    const locale = language === 'English' ? 'en' : 'it';
    await expect(page.locator('.save-date-link')).toHaveAttribute('href', `/calendar/wedding-${locale}.ics`);
    const pending = page.waitForEvent('download');
    await page.locator('.save-date-link').click();
    const download = await pending;
    expect(download.suggestedFilename()).toBe('andrea-sara-wedding.ics');
    const {readFile} = await import('node:fs/promises');
    const data = await readFile((await download.path())!, 'utf8');
    expect(data).toContain('DTSTART:20270520T143000Z');
    expect(data).toContain('DTEND:20270520T220000Z');
    expect(data).toContain('Villa Valentina');
  }
});


test('scroll reveal stays pinned and chapter destinations align with the viewport', async ({ page }, testInfo) => {
  await page.goto('/');
  await expect(page.locator('.chapter-trigger')).toBeEnabled();
  await expect(page.locator('.skip-opening')).toBeVisible();
  await page.evaluate(() => window.scrollTo({ top: 30, behavior: 'instant' }));
  await expect.poll(async () => (await page.locator('.envelope-stage').boundingBox())!.y).toBeCloseTo(0, 0);
  await expect(page.locator('.hero .invitation-link')).toHaveAttribute('inert', '');
  await page.getByRole('button', { name: 'Scroll to reveal' }).click();
  await expect(page.locator('.envelope-scene')).toHaveClass(/opened/);
  if (testInfo.project.use.isMobile) await expect(page.locator('.header-date')).toBeHidden();
  for (const id of ['story', 'details', 'ceremony-visions', 'travel', 'rsvp', 'memories']) {
    await page.locator('.chapter-trigger').click();
    await page.locator(`.chapter-nav a[href="#${id}"]`).click();
    await expect.poll(async () => (await page.locator(`#${id}`).boundingBox())!.y).toBeCloseTo(0, 0);
  }
  expect(await page.evaluate(() => document.body.scrollWidth)).toBe(await page.evaluate(() => innerWidth));
});

test('rings visibly follow scroll progress through the viewport', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('.chapter-trigger')).toBeEnabled();
  const rings = page.locator('.joined-rings');
  const ring = rings.locator('span').first();
  const progress = () => rings.evaluate(el => Number((el as HTMLElement).style.getPropertyValue('--ring-progress')));
  const initial = await ring.evaluate(el => getComputedStyle(el).transform);
  await rings.evaluate(el => window.scrollTo({ top: scrollY + el.getBoundingClientRect().top - innerHeight * .65, behavior: 'instant' }));
  await expect.poll(progress).toBeGreaterThan(.4);
  expect(await progress()).toBeLessThan(.7);
  const intermediate = await ring.evaluate(el => getComputedStyle(el).transform);
  await rings.evaluate(el => window.scrollTo({ top: scrollY + el.getBoundingClientRect().top - innerHeight * .3, behavior: 'instant' }));
  await expect.poll(progress).toBe(1);
  const final = await ring.evaluate(el => getComputedStyle(el).transform);
  expect(intermediate).not.toBe(initial);
  expect(intermediate).not.toBe(final);
});
