import { test, expect } from '@playwright/test';
import { openReplyForm } from './rsvp-form';

test('switch language, preserve form input and remember choice', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Andrea & Sara', exact: true }).first()).toBeVisible();
  await page.getByLabel('Your invitation code').fill('NOT-SUBMITTED');
  await page.getByRole('button', { name: 'Italiano', exact: true }).click();
  await expect(page.locator('html')).toHaveAttribute('lang', 'it');
  await expect(page.getByLabel('Inserisci il codice')).toHaveValue('NOT-SUBMITTED');
  await expect(page.getByText("Ci sposiamo! E non vediamo l'ora di festeggiarlo insieme a te.")).toBeVisible();
  await expect(page.getByRole('link', { name: 'Carica le tue foto/video ↗' })).toBeAttached();
  await expect(page.locator('.gallery')).toHaveCount(0);
  await expect(page.locator('body')).toHaveJSProperty('scrollWidth', await page.evaluate(() => document.documentElement.clientWidth));
  await page.reload();
  await expect(page.getByRole('button', { name: 'Italiano', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('html')).toHaveAttribute('lang', 'it');
  await page.getByRole('button', { name: 'English', exact: true }).click();
  await expect(page.getByLabel('Your invitation code')).toBeAttached();
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
});

test('Italian browser defaults to Italian and reduced motion disables animations', async ({ browser }, testInfo) => {
  const context = await browser.newContext({ locale: 'it-IT', reducedMotion: 'reduce', viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  await page.goto(process.env.WEB_URL || 'http://localhost:5173');
  await expect(page.locator('html')).toHaveAttribute('lang', 'it');
  await expect(page.getByRole('button', { name: 'Italiano', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('.envelope').first()).toHaveCSS('display', 'none');
  await expect(page.locator('body')).toHaveJSProperty('scrollWidth', 390);
  await page.screenshot({ path: testInfo.outputPath('landing-italian-mobile.png'), fullPage: true });
  await context.close();
});

test('Italian invitation and RSVP', async ({ page }) => {
  await page.goto('/#invite=DEMO-LOVE-2027');
  await openReplyForm(page);
  await page.getByRole('button', { name: 'Italiano', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Benvenuto, Dear friends.' })).toBeVisible();
  await page.getByLabel('Indirizzo email').fill('italian-browser@example.com');
  await page.getByLabel('Nome e cognome').first().fill('Ospite italiano');
  await page.getByRole('button', { name: 'Invia la nostra risposta ↗' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Ci siete anche voi!' })).toBeVisible();
  await page.reload();
  await openReplyForm(page);
  await expect(page.getByLabel('Nome e cognome').first()).toHaveValue('Ospite italiano');
  await page.getByRole('button', { name: 'Esci', exact: true }).click();
});

test('venue, travel, Akamaru and hero never overlap on a narrow screen', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 375, height: 667 });
  await page.goto('/');
  await page.getByRole('button', { name: 'Italiano', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Andrea & Sara', exact: true }).first()).toBeVisible();
  await expect(page.locator('.hero-date')).toContainText('20 maggio 2027');
  await page.evaluate(() => document.documentElement.style.fontSize = '22px');
  await page.getByRole('button', { name: 'Scorri in basso' }).click();
  await expect.poll(() => page.locator('.envelope-scene').evaluate(el => Number(getComputedStyle(el).getPropertyValue('--page-reveal')))).toBe(1);
  const button = await page.locator('.hero .invitation-link').boundingBox();
  expect(button!.height).toBeGreaterThanOrEqual(44);
  await expect(page.locator('.skip-opening')).toHaveAttribute('inert', '');
  await expect(page.locator('body')).toHaveJSProperty('scrollWidth', 375);
  await expect(page.locator('#travel')).toContainText('Via Donizetti 17');

  await expect(page.getByRole('img', { name: 'Il nostro bassotto Akamaru', exact: true })).toHaveAttribute('src', '/images/akamaru.webp');
  await expect(page.locator('#travel iframe')).toHaveCount(0);
  await page.route('https://maps.google.com/**', route => route.fulfill({ contentType: 'text/html', body: '<p>Map embed requested</p>' }));
  await page.getByRole('button', { name: 'Mostra la mappa' }).click();
  await expect(page.locator('#travel iframe')).toHaveAttribute('src', /Villa%20Valentina/);
  await page.evaluate(() => document.documentElement.style.fontSize = '18px');
  await page.screenshot({ path: testInfo.outputPath('andrea-sara-mobile.png'), fullPage: true });
});
