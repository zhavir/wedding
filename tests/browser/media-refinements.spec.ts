import { test, expect } from './fixtures';

const images = [
  { id: 'portrait', width: 600, height: 900, orientation: 'portrait' },
  { id: 'landscape', width: 1600, height: 900, orientation: 'landscape' },
  { id: 'square', width: 800, height: 800, orientation: 'square' }
];

for (const seats of [1, 2]) {
  test(`named S3 images, uncropped carousel and ${seats} reserved seats`, async ({ page }, info) => {
    await page.emulateMedia({ reducedMotion: seats === 1 ? 'reduce' : 'no-preference' });
    await page.route('**/*.webp', route => route.fulfill({
      contentType: 'image/svg+xml',
      body: '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="900"><rect width="600" height="900" fill="#9eaa98"/></svg>'
    }));
    await page.route('**/api/session', route => route.fulfill({ json: {
      id: 'guest', name: 'Guest', max_guests: seats, is_admin: false, is_witness: false, language: 'en'
    } }));
    await page.route('**/api/rsvp', route => route.fulfill({ status: 404, json: {} }));
    await page.route('**/api/photos/carousel', route => route.fulfill({ json: { items: images.map(image => ({
      ...image, caption: `Caption ${image.id}`,
      preview: `data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="${image.width}" height="${image.height}"><rect width="100%" height="100%" fill="#9eaa98"/></svg>`)}`
    })) } }));
    await page.goto('/');
    await expect(page.locator('.carousel .group').first().locator('figure')).toHaveCount(3);
    for (const image of images) {
      const figure = page.locator(`.carousel .group:first-child figure.${image.orientation}`);
      await expect(figure.locator('figcaption')).toHaveText(`Caption ${image.id}`);
      await expect(figure.locator('img')).toHaveCSS('object-fit', 'contain');
      const ratio = await figure.locator('img').evaluate(el => el.clientWidth / el.clientHeight);
      expect(ratio).toBeCloseTo(image.width / image.height, 2);
    }
    await expect(page.locator('.story-keepsakes figcaption')).toHaveCount(6);
    const sources = await page.locator('.hero img, .story-keepsakes img, .dream img, .comparison img, .venue-photo img').evaluateAll(elements => elements.map(el => (el as HTMLImageElement).src));
    if (sources.length) {
      expect(sources).toHaveLength(13);
      const base = sources[0].slice(0, sources[0].lastIndexOf('/'));
      expect(sources.every(src => src.startsWith(`${base}/`))).toBe(true);
      expect(sources).toContain(`${base}/venue-photo-1.webp`);
      expect(sources).toContain(`${base}/venue-photo-2.webp`);
      await expect(page.locator('link[rel="icon"]')).toHaveAttribute('href', `${base}/favicon.svg`);
      expect(sources.some(src => src.includes('/images/'))).toBe(false);
    } else {
      // Local previews without PUBLIC_ASSET_URL deliberately show placeholders.
      await expect(page.locator('.hero .picture-placeholder, .story-keepsakes .picture-placeholder, .dream .picture-placeholder, .comparison .picture-placeholder, .venue-photo .picture-placeholder')).toHaveCount(13);
      await expect(page.locator('link[rel="icon"]')).toHaveCount(0);
    }
    await page.getByRole('button', { name: 'Italiano', exact: true }).click();
    await expect(page.locator('.rsvp-card')).toContainText(seats === 1 ? 'Abbiamo riservato 1 posto per te.' : 'Abbiamo riservato 2 posti per voi.');
    if (info.project.name === 'desktop') {
      await page.locator('.envelope-scene').evaluate(el => window.scrollTo({ top: (el as HTMLElement).offsetTop + el.clientHeight - innerHeight, behavior: 'instant' }));
      await expect(page.locator('.site-header')).toHaveClass(/identity-revealed/);
      await expect.poll(async () => page.locator('.header-identity').evaluate(el => {
        const capsule = el.getBoundingClientRect();
        const logo = el.querySelector('.monogram')!.getBoundingClientRect();
        const date = el.querySelector('.header-date')!.getBoundingClientRect();
        return Math.abs((capsule.right - date.right) - (logo.left - capsule.left) - 6);
      })).toBeLessThan(1.5);
    }
  });
}
