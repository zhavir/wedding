import { test as base, expect } from '@playwright/test';

// These flows assert English copy. Default-language tests use an unmodified page.
export const test = base.extend({
  page: async ({ page }, use) => {
    await page.addInitScript(() => {
      if (!localStorage.getItem('wedding-language'))
        localStorage.setItem('wedding-language', 'en');
    });
    await use(page);
  },
});

export { expect };
