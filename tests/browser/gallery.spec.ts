import { readFileSync } from 'node:fs';
import { previewImage } from './media-fixtures';
import { memoryImage } from './media-fixtures';
import { test, expect } from './fixtures';

test('upload supports multiple selection and desktop file drops', async ({ page }) => {
  await page.goto('/gallery#invite=DEMO-LOVE-2027');
  const input = page.getByLabel('Choose photos and videos');
  await expect(input).toHaveAttribute('multiple', '');
  await input.setInputFiles([
    { name: 'first.png', mimeType: 'image/png', buffer: Buffer.from('first') },
    { name: 'second.png', mimeType: 'image/png', buffer: Buffer.from('second') },
  ]);
  await expect(page.locator('.selected-preview')).toHaveCount(2);
await page.getByRole('button', { name: 'Remove first.png', exact: true }).click();
await expect(page.locator('.selected-preview')).toHaveCount(1);
expect(await input.evaluate((element: HTMLInputElement) => Array.from(element.files || []).map(file => file.name))).toEqual(['second.png']);
await page.getByRole('button', { name: 'Remove second.png', exact: true }).click();
await expect(page.locator('.selected-preview')).toHaveCount(0);
await expect(page.getByRole('button', { name: 'Share the love ↗' })).toBeDisabled();
await input.setInputFiles({ name: 'first.png', mimeType: 'image/png', buffer: Buffer.from('first') });
await expect(page.locator('.selected-preview')).toHaveCount(1);
  const transfer = await page.evaluateHandle(() => {
    const data = new DataTransfer();
    data.items.add(new File(['image'], 'dropped.png', { type: 'image/png' }));
    data.items.add(new File(['video'], 'dropped.mp4', { type: 'video/mp4' }));
    data.items.add(new File(['image'], 'another.png', { type: 'image/png' }));
    return data;
  });
  await page.locator('body').dispatchEvent('dragenter', { dataTransfer: transfer });
await expect(page.getByText('Drop photos and videos', { exact: true })).toBeVisible();
await page.locator('#upload').dispatchEvent('dragenter', { dataTransfer: transfer });
await page.locator('#upload').dispatchEvent('dragleave', { dataTransfer: transfer });
await expect(page.locator('.media-drop-overlay')).toBeVisible();
await page.locator('body').dispatchEvent('dragleave', { dataTransfer: transfer });
await expect(page.locator('.media-drop-overlay')).toHaveCount(0);
await page.locator('body').dispatchEvent('dragenter', { dataTransfer: transfer });
await page.locator('body').dispatchEvent('drop', { dataTransfer: transfer });
await expect(page.locator('.media-drop-overlay')).toHaveCount(0);
  await expect(page.locator('.selected-preview')).toHaveCount(3);
});

test('gallery has its own authentication gate and lost-code flow', async ({ page, context }) => {
  await page.goto('/');
  await expect(page.locator('.gallery')).toHaveCount(0);
  await expect(page.locator('input[type=file]')).toHaveCount(0);
  await page.getByRole('link', { name: 'Upload your photos/videos ↗' }).click();
  await expect(page.getByLabel('Your invitation code')).toBeVisible();
  await expect(page.getByLabel('Choose photos and videos')).toHaveCount(0);
  await page.getByRole('button', { name: 'Lost your code?' }).click();
  await page.getByLabel('Invitation email address').fill('not-invited@example.com');
  await page.getByRole('button', { name: 'Email me a replacement code' }).click();
  await expect(page.getByRole('status')).toContainText('If this email belongs to an active invitation');
  await page.getByLabel('Your invitation code').fill('DEMO-LOVE-2027');
  await page.getByRole('button', { name: 'Open my invitation ↗' }).click();
  await expect(page.getByLabel('Choose photos and videos')).toBeVisible();
  await page.reload();
  await expect(page.getByLabel('Choose photos and videos')).toBeVisible();
  // Finish requests that renew the cookie before simulating its removal.
  await page.waitForLoadState('networkidle');
  await context.clearCookies();
  await page.reload();
  await expect(page.getByLabel('Your invitation code')).toBeVisible();
  await expect(page.getByLabel('Choose photos and videos')).toHaveCount(0);
});

test('email gallery link establishes a persistent session', async ({ page }) => {
  await page.goto('/gallery#invite=DEMO-LOVE-2027');
  await expect(page.getByLabel('Choose photos and videos')).toBeVisible();
  await expect(page).toHaveURL(/\/gallery#upload$/);
  await page.reload();
  await expect(page.getByLabel('Choose photos and videos')).toBeVisible();
});

test('explicit pagination, load all and viewer navigation across pages', async ({ page, isMobile }) => {
  const requests: number[] = [];
  let failNext = false;
  await page.route(/\/api\/photos(?:\?.*)?$/, async route => {
    const offset = Number(new URL(route.request().url()).searchParams.get('cursor') || 0);
    requests.push(offset);
    if (failNext) {
      failNext = false;
      await route.fulfill({ status: 503, json: { detail: 'Please retry.' } });
      return;
    }
    const count = Math.min(12, 29 - offset);
    await route.fulfill({ json: {
      items: Array.from({ length: count }, (_, index) => ({
        id: `photo-${offset + index}`, caption: `Memory ${offset + index + 1}`,
        preview: previewImage, original: '/original-download'
      })),
      cursor: offset + count < 29 ? String(offset + count) : null
    } });
  });
  await page.goto('/gallery#invite=DEMO-LOVE-2027');
  await expect(page.locator('.photo-card')).toHaveCount(12);
  await page.getByRole('button', { name: 'Load more memories ↓' }).scrollIntoViewIfNeeded();
  await expect.poll(() => requests.length).toBe(1);
  await page.locator('.photo-card').last().click();
  const viewer = page.getByRole('dialog', { name: 'Wedding photo viewer' });
  await expect(viewer).toBeVisible();
  await expect(viewer.getByRole('img')).toHaveAttribute('alt', 'Memory 12');
  failNext = true;
  await viewer.getByRole('button', { name: 'Next photo' }).click();
  await expect(viewer.getByRole('alert')).toContainText('Please retry.');
  if (isMobile) {
    const stage = viewer.locator('.viewer-stage');
    await stage.dispatchEvent('pointerdown', { pointerType: 'touch', clientX: 260, clientY: 200 });
    await stage.dispatchEvent('pointerup', { pointerType: 'touch', clientX: 60, clientY: 210 });
  } else {
    await page.keyboard.press('ArrowRight');
  }
  await expect(viewer.getByRole('img')).toHaveAttribute('alt', 'Memory 13');
  await expect(page.locator('.photo-card')).toHaveCount(24);
  await viewer.getByRole('button', { name: 'Previous photo' }).click();
  await expect(viewer.getByRole('img')).toHaveAttribute('alt', 'Memory 12');
  await page.keyboard.press('Escape');
  await expect(viewer).toHaveCount(0);
  await expect(page.locator('.photo-card').nth(11)).toBeFocused();
  await page.getByRole('button', { name: 'Load all photos' }).click();
  await expect(page.locator('.photo-card')).toHaveCount(29);
  await expect(page.getByRole('button', { name: 'Load all photos' })).toHaveCount(0);
  await page.locator('.photo-card').last().click();
  await expect(viewer.getByRole('button', { name: 'Next photo' })).toBeDisabled();
  await viewer.getByRole('button', { name: 'Close photo viewer' }).click();
  await page.getByRole('button', { name: 'Refresh gallery ↻' }).click();
  await expect(page.locator('.photo-card')).toHaveCount(12);
  await page.getByRole('button', { name: 'Load more memories ↓' }).click();
  await expect(page.locator('.photo-card')).toHaveCount(24);
});

test('gallery accepts a mixed image and video batch', async ({ page }) => {
  await page.goto('/gallery#invite=DEMO-LOVE-2027');
  await page.getByLabel('Choose photos and videos').setInputFiles([memoryImage, { name: 'memory.mp4', mimeType: 'video/mp4', buffer: readFileSync('tests/browser/memory.mp4') }]);
  const completions: string[] = [];
  page.on('request', request => {
    if (/\/api\/photos\/[^/]+\/complete$/.test(request.url())) completions.push(request.url());
  });
  await page.getByRole('button', { name: /Share the love/ }).click();
  await expect(page.getByText('2 memories received.', { exact: false })).toBeVisible({ timeout: 30000 });
  expect(new Set(completions).size).toBe(2);
});
