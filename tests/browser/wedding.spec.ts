import { memoryImage } from './media-fixtures';
import { randomUUID } from 'node:crypto';
import { test, expect } from './fixtures';
import { openReplyForm } from './rsvp-form';

test('landing page, invitation and RSVP', async ({ page, context }) => {
  await page.goto('/');
  const videoLink = page.getByRole('link', { name: "Oh, e dic sì, 'nda fess e sor't!" });
  await expect(videoLink).toHaveCSS('text-decoration-line', 'underline');
  await expect(videoLink.locator('svg')).toHaveAttribute('aria-hidden', 'true');
  await expect(page.getByRole('heading', { name: 'Andrea & Sara', exact: true }).first()).toBeVisible();
  await expect(page.locator('body')).toHaveJSProperty('scrollWidth', await page.evaluate(() => document.documentElement.clientWidth));
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: /RSVP/ }).click();
  await page.getByLabel('Your invitation code').fill('DEMO-LOVE-2027');
  await page.getByRole('button', { name: /Open my invitation/ }).click();
  await expect(page.getByRole('heading', { name: /Welcome, Dear friends/ })).toBeVisible();
  await openReplyForm(page);
  await page.getByLabel('Will you be joining us?').selectOption({ label: 'Joyfully accepts' });
  await page.getByLabel('Email address').fill('browser@example.com');
  await page.getByLabel('Full name').first().fill('Browser guest');
  await expect(page.locator('input[type=checkbox]')).toHaveCount(0);
  await page.getByRole('button', { name: /Send (my|our) reply/ }).click();
  await expect(page.getByText('You’re on the list!', { exact: false })).toBeVisible();
  await expect(page.locator('canvas.celebration')).toBeVisible();
  await expect(page.getByRole('button', { name: /Send (my|our) reply/ })).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole('button', { name: 'Edit your preferences' })).toBeVisible();
  await expect(page.getByRole('button', { name: /Send (my|our) reply/ })).toHaveCount(0);
  await page.getByRole('button', { name: 'Edit your preferences' }).click();
  await expect(page.getByLabel('Email address', { exact: true })).toHaveValue('browser@example.com');
  await expect(page.getByLabel('Email address', { exact: true })).toHaveAttribute('required', '');
  await page.waitForLoadState('networkidle');
  await context.clearCookies();
  await page.reload();
  await page.getByLabel('Your invitation code').fill('DEMO-LOVE-2027');
  await page.getByRole('button', { name: /Open my invitation/ }).click();
  await expect(page.getByLabel('Email address', { exact: true })).toHaveValue('browser@example.com');
  await expect(page.getByRole('button', { name: 'Edit your preferences' })).toHaveCount(0);
  await page.getByRole('link', { name: 'Upload your photos/videos ↗' }).click();
  await expect(page).toHaveURL(/\/gallery#upload/);
  await page.getByLabel('Choose photos and videos').setInputFiles(memoryImage);
  await page.getByLabel('A little caption').fill('A browser-tested memory');
  await page.getByRole('button', { name: /Share the love/ }).click();
  await expect(page.getByText('1 memories received.', { exact: false })).toBeVisible({ timeout: 30000 });
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page.getByLabel('Your invitation code')).toBeVisible();
});

test('bad invitation displays useful feedback', async ({ page }) => {
  await page.goto('/#rsvp');
  await page.getByLabel('Your invitation code').fill('WRONG-INVITE');
  await page.getByRole('button', { name: /Open my invitation/ }).click();
  await expect(page.locator('.rsvp-card').getByRole('status')).toContainText('check your code');
});


test('an invalid email link displays its error only once', async ({ page }) => {
  await page.goto('/#invite=INVALID-LINK-1234');
  await expect(page.getByText("We couldn't find that invitation. Please check your code.", { exact: true })).toHaveCount(1);
  await page.getByLabel('Your invitation code').fill('INVALID-CODE-1234');
  await page.getByRole('button', { name: /Open my invitation/ }).click();
  await expect(page.getByText("We couldn't find that invitation. Please check your code.", { exact: true })).toHaveCount(1);
});

test('saved witness reply is personalized and only opens for explicit editing', async ({ page }) => {
  await page.request.post('/api/session', { headers: { Origin: 'http://web:5173' }, data: { code: 'DEMO-ADMIN-2027' } });
  const created = await page.request.post('/api/admin/invitations', { headers: { Origin: 'http://web:5173' }, data: { invitations: [{ name: 'Giulia', email: `witness-${randomUUID()}@example.com`, is_witness: true, language: 'en' }] } });
  expect(created.ok(), await created.text()).toBeTruthy();
  const invite = (await created.json()).items[0];
  await page.goto('/' + new URL(invite.link).hash);
  await expect(page.getByRole('heading', { name: 'Will you be our witness?' })).toBeVisible();
  await page.getByLabel('Yes, I accept the role of wedding witness.').check();
  await page.getByRole('button', { name: /Send (my|our) reply ↗/ }).click();
  await expect(page.getByRole('button', { name: 'Edit your preferences', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: /Send (my|our) reply ↗/ })).toHaveCount(0);
  await page.getByRole('link', { name: 'Upload your photos/videos ↗' }).click();
  await page.getByRole('link', { name: '← Back to our wedding' }).click();
  await expect(page.getByRole('button', { name: 'Edit your preferences', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: /Send (my|our) reply ↗/ })).toHaveCount(0);
  await page.reload();
  await openReplyForm(page);
  await expect(page.getByRole('button', { name: /Send (my|our) reply ↗/ })).toBeEnabled();
  await expect(page.getByLabel('Yes, I accept the role of wedding witness.')).toBeChecked();
});

test('additional guest receives a personal invitation that expires after rejection', async ({ page, browser }) => {
  const admin = await browser.newContext({ baseURL: process.env.WEB_URL || 'http://localhost:5173' });
  const headers = { Origin: 'http://web:5173' };
  await admin.request.post('/api/session', { headers, data: { code: 'DEMO-ADMIN-2027' } });
  const created = await admin.request.post('/api/admin/invitations', { headers, data: { invitations: [{ name: 'Party host', email: `party-${randomUUID()}@example.com`, max_guests: 2, language: 'en' }] } });
  expect(created.ok(), await created.text()).toBeTruthy();
  const parent = (await created.json()).items[0];
  await page.goto('/' + new URL(parent.link).hash);
  await expect(page.locator('header').getByRole('link', { name: 'Gallery', exact: true })).toBeVisible();
  await page.getByRole('button', { name: '+ Add another guest', exact: true }).click();
  const email = `additional-${Date.now()}@example.com`;
  await page.getByLabel('Additional guest email').fill(email);
  await page.getByLabel('Full name', { exact: true }).nth(1).fill('Alex');
  await page.getByRole('button', { name: /Send (my|our) reply ↗/ }).click();
  await expect(page.getByRole('button', { name: 'Edit your preferences' })).toBeVisible();
  const list = await admin.request.get('/api/admin/invitations');
  const child = (await list.json()).items.find((item: { email: string }) => item.email === email);
  expect(child.email_status).toBe('sent');
  const guest = await browser.newContext({ baseURL: process.env.WEB_URL || 'http://localhost:5173' });
  const guestPage = await guest.newPage();
  await guestPage.goto('/gallery' + new URL(child.link).hash);
  await expect(guestPage.getByLabel('Choose photos and videos')).toBeVisible();
  await page.getByRole('button', { name: 'Edit your preferences' }).click();
  await page.getByLabel('Will you be joining us?').selectOption('false');
  await page.getByRole('button', { name: /Send (my|our) reply ↗/ }).click();
  await expect(page.getByRole('button', { name: 'Edit your preferences' })).toBeVisible();
  await guestPage.reload();
  await expect(guestPage.getByLabel('Your invitation code')).toBeVisible();
  const refreshed = await admin.request.get('/api/admin/invitations');
  expect((await refreshed.json()).items.find((item: { id: string }) => item.id === child.id).active).toBe(false);
  await guest.close();
  await admin.close();
});
