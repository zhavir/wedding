import { expect, type Page } from '@playwright/test';

export async function openReplyForm(page: Page) {
  await page.waitForLoadState('networkidle');
  const edit = page.getByRole('button', { name: /Edit your preferences|Modifica(?:te)? le (?:tue|vostre) preferenze/ });
  if (await edit.isVisible()) await edit.click();
  await expect(page.locator('input[type="email"]').first()).toBeVisible();
}
