import { test, expect } from '@playwright/test';

test('invitation unties, chapter links skip ahead, and the footer ties again', async ({ page }, testInfo) => {
  await page.goto('/');
  const opening = page.locator('.opening-scene');
  await expect(page.locator('.curtain-cue')).toBeInViewport();
  await expect(page.getByRole('button', { name: 'Open our invitation' })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('invitation-closed.png') });
  await page.getByRole('button', { name: 'Open our invitation' }).click();
  await expect.poll(() => opening.evaluate(el => Number(getComputedStyle(el).getPropertyValue('--opening')))).toBeGreaterThan(.9);
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
  await expect(page.locator('.hero-monogram, .curtain-seal')).toHaveCount(0);
  await expect(page.locator('.curtain-cue')).toBeHidden();
  await expect(page.locator('.curtain').first()).toBeHidden();
  await expect(page.locator('.hero h1')).toBeVisible();
  await page.locator('.ribbon-timeline').scrollIntoViewIfNeeded();
  await expect(page.locator('.thread-progress')).toHaveAttribute('stroke-dashoffset', '0');
  await expect(page.locator('.timeline-bead')).toBeHidden();
});


test('menu placeholders, botanical borders and chapter picker are available in both languages', async ({ page }, testInfo) => {
  await page.goto('/');
  await expect(page.locator('.botanical-frame').first()).toBeVisible();
  await expect(page.locator('link[rel="icon"]')).toHaveAttribute('href', /\/favicon\.svg$/);
  const picker = page.locator('.chapter-trigger');
  await picker.click();
  await page.getByRole('navigation', { name: 'Jump to a chapter' }).getByRole('link', { name: /At the table/ }).click();
  await expect(page).toHaveURL(/#menu$/);
  await expect(page.locator('#menu')).toContainText('The menu is a placeholder for now.');
  await page.getByRole('button', { name: 'Italiano', exact: true }).click();
  await expect(page.locator('#menu')).toContainText('Il menu è ancora provvisorio.');
  await page.locator('#menu').scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath('menu-italian.png') });
  await picker.click();
  await page.keyboard.press('Escape');
  await expect(picker).toHaveAttribute('aria-expanded', 'false');
  await expect(picker).toBeFocused();
});


test('chapter dock expands without rotating labels and gallery shares the masthead', async ({ page }, testInfo) => {
  await page.goto('/');
  const header = page.locator('.site-header');
  const homeHeader = await header.boundingBox();
  const dock = page.locator('.chapter-picker');
  const trigger = page.getByRole('button', { name: 'Explore the chapters' });
  const closed = await dock.boundingBox();
  await trigger.click();
  await expect(trigger).toHaveAttribute('aria-expanded', 'true');
  await expect.poll(async () => (await dock.boundingBox())!.height).toBeGreaterThan(300);
  await expect(page.locator('.picker-label')).toHaveCSS('transform', 'none');
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

test('curtains conceal the invitation, fold open and hold before the story', async ({ page }, testInfo) => {
  await page.goto('/');
  const opening = page.locator('.opening-scene');
  await expect(page.locator('.curtain-cue')).toBeInViewport();
  await expect.poll(() => opening.evaluate(el => Number(getComputedStyle(el).getPropertyValue('--opening')))).toBe(0);
  expect(await page.locator('.curtain-left').evaluate(el => Number(getComputedStyle(el).zIndex))).toBeGreaterThan(await page.locator('.hero').evaluate(el => Number(getComputedStyle(el).zIndex)));
  await expect(page.locator('.hero .invitation-link')).toHaveAttribute('inert', '');
  await expect(page.locator('.invitation-venue')).toHaveJSProperty('complete', true);
  const height = await page.evaluate(() => innerHeight);
  await page.evaluate(y => window.scrollTo({top: y, behavior: 'instant'}), height * .32);
  await expect.poll(() => opening.evaluate(el => Number(getComputedStyle(el).getPropertyValue('--opening')))).toBeGreaterThan(.4);
  await page.screenshot({path: testInfo.outputPath('curtain-fold.png')});
  await page.evaluate(y => window.scrollTo({top: y, behavior: 'instant'}), height * .68);
  await expect.poll(() => opening.evaluate(el => Number(getComputedStyle(el).getPropertyValue('--opening')))).toBe(1);
  const before = await page.locator('.opening-stage').boundingBox();
  await page.evaluate(y => window.scrollTo({top: y, behavior: 'instant'}), height * .98);
  await page.waitForTimeout(100);
  const after = await page.locator('.opening-stage').boundingBox();
  expect(Math.abs(after!.y - before!.y)).toBeLessThan(2);
  await expect(page.locator('.hero .invitation-link')).not.toHaveAttribute('inert');
  await page.screenshot({path: testInfo.outputPath('invitation-held-open.png')});
  await page.locator('footer').scrollIntoViewIfNeeded();
  const divider = await page.locator('.footer-bottom').boundingBox();
  const phrases = await page.locator('.marquee').boundingBox();
  expect(phrases!.y).toBeGreaterThan(divider!.y + divider!.height);
  await expect(page.locator('.marquee')).toContainText('Stay for one more dance');
  await expect(page.locator('.marquee')).not.toContainText('Andrea');
  await page.getByRole('button', {name: 'Italiano', exact: true}).click();
  await expect(page.locator('.marquee')).toContainText('Ancora un ballo insieme');
});

test('timeline ink tracks its marker through the end and Akamaru resets outside the portrait', async ({ page }, testInfo) => {
  await page.goto('/');
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
  if (!testInfo.project.use.isMobile) {
    await page.locator('.dog-portrait').hover();
    await expect(page.locator('.dog-secret')).toHaveCSS('opacity', '1');
    await page.locator('.dog-picture > p').hover();
    await expect(page.locator('.dog-secret')).toHaveCSS('opacity', '0');
    await expect(page.locator('.dog-portrait img')).toHaveCSS('transform', 'none');
  }
});

test('curtain reveal has a disappearing cue, two header islands and a plain invitation link', async ({ page }, testInfo) => {
  await page.goto('/');
  await expect(page.locator('.curtain-cue')).toContainText('Scroll to reveal');
  await expect(page.locator('.curtain-seal, .hero-monogram, .hero .flourish')).toHaveCount(0);
  await expect(page.locator('.fabric-pleat')).toHaveCount(24);
  const identity = await page.locator('.header-identity').boundingBox();
  const actions = await page.locator('.header-actions').boundingBox();
  expect(actions!.x - identity!.x - identity!.width).toBeGreaterThanOrEqual(9);
  await expect(page.locator('.site-header')).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)');
  await expect(page.locator('.site-header')).toHaveCSS('backdrop-filter', 'none');
  await page.screenshot({path: testInfo.outputPath('fabric-closed.png')});
  await page.evaluate(() => window.scrollTo({top: 30, behavior: 'instant'}));
  await expect(page.locator('.curtain-cue')).toBeHidden();
  await page.evaluate(() => window.scrollTo({top: innerHeight * .32, behavior: 'instant'}));
  await page.waitForTimeout(200);
  await page.screenshot({path: testInfo.outputPath('fabric-opening.png')});
  await page.evaluate(() => window.scrollTo({top: innerHeight * .68, behavior: 'instant'}));
  await expect(page.locator('.invitation-link')).not.toHaveAttribute('inert');
  await expect(page.locator('.invitation-link')).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)');
  await expect(page.locator('.invitation-link')).toHaveCSS('box-shadow', 'none');
  await page.screenshot({path: testInfo.outputPath('fabric-open.png')});
});

test('curtain hems lead the tops, the date waits, and the reveal stays open until reload', async ({ page }, testInfo) => {
  await page.goto('/');
  await expect(page.locator('.header-date')).toHaveCSS('opacity', '0');
  await page.evaluate(() => scrollTo({top: innerHeight * .32, behavior: 'instant'}));
  await page.waitForTimeout(200);
  const edges = await page.locator('.curtain-left').evaluate((svg: SVGSVGElement) => {
    const paths = Array.from(svg.querySelectorAll('path'));
    const edge = (y: number) => {
      const point = svg.createSVGPoint(); point.y = y;
      for (let x = 100; x >= 0; x--) { point.x = x; if (paths.some(path => path.isPointInFill(point))) return x; }
      return 0;
    };
    return [edge(150), edge(850)];
  });
  expect(edges[0] - edges[1]).toBeGreaterThan(15);
  await expect(page.locator('.header-date')).toHaveCSS('opacity', '0');
  await page.screenshot({path: testInfo.outputPath('curved-curtain-half.png')});
  await page.evaluate(() => scrollTo({top: innerHeight * .7, behavior: 'instant'}));
  await expect(page.locator('.opening-scene')).toHaveClass(/opened/);
  await expect(page.locator('.header-date')).toHaveCSS('opacity', '1');
  await page.evaluate(() => scrollTo({top: 0, behavior: 'instant'}));
  await expect(page.locator('.opening-scene')).toHaveClass(/opened/);
  await expect(page.locator('.curtain-cue')).toBeHidden();
  await expect(page.locator('.cherry-petal').first()).toHaveCSS('animation-name', 'petal-drift');
  await page.screenshot({path: testInfo.outputPath('open-with-cherry-blossoms.png')});
  await page.reload();
  await expect(page.locator('.curtain-cue')).toBeVisible();
  await expect(page.locator('.header-date')).toHaveCSS('opacity', '0');
});

test('save the date downloads the all-day wedding event in both languages', async ({ page }) => {
  await page.emulateMedia({reducedMotion: 'reduce'});
  await page.goto('/');
  for (const language of ['English', 'Italiano']) {
    await page.getByRole('button', {name: language, exact: true}).click();
    const pending = page.waitForEvent('download');
    await page.locator('.save-date-link').click();
    const download = await pending;
    expect(download.suggestedFilename()).toBe('andrea-sara-wedding.ics');
    const {readFile} = await import('node:fs/promises');
    const data = await readFile((await download.path())!, 'utf8');
    expect(data).toContain('DTSTART;VALUE=DATE:20270520');
    expect(data).toContain('DTEND;VALUE=DATE:20270521');
    expect(data).toContain('Villa Valentina');
  }
});
