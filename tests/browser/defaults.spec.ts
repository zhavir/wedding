import { test, expect } from '@playwright/test';

test('Italian is the default even in an English browser, and explicit choices persist', async ({ page }) => {
  await page.route('**/api/session', route => route.fulfill({ status: 401, json: {} }));
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  await expect(page.locator('html')).toHaveAttribute('lang', 'it');
  await page.getByRole('button', { name: 'English', exact: true }).click();
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await page.evaluate(() => localStorage.setItem('wedding-language', 'invalid'));
  await page.goto('/gallery');
  await expect(page.locator('html')).toHaveAttribute('lang', 'it');
});

test('carousel captions match the story caption color', async ({ page }) => {
  await page.route('**/api/session', route => route.fulfill({ json: {
    id: 'guest', name: 'Mario Rossi', max_guests: 2, is_admin: false, language: 'it'
  } }));
  await page.route('**/api/photos/carousel', route => route.fulfill({ json: { items: [{
    id: 'photo', caption: 'Un bel ricordo', width: 100, height: 100,
    preview: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"/>'
  }] } }));
  await page.goto('/');
  await expect(page.locator('.carousel figcaption').first()).toBeAttached();
  const color = await page.locator('#story figcaption').first().evaluate(el => getComputedStyle(el).color);
  expect(color).toBe('rgb(73, 106, 85)');
  await expect(page.locator('.carousel figcaption').first()).toHaveCSS('color', color);
});
