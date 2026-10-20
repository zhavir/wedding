# Personalise the wedding

Edit `locales/en/wedding.json` to change the names, dates, venue, contact address, story, event schedule, FAQs, image paths, and email subject/body/button/footer. Both the website and invitation emails read this same file. Keep JSON valid; run the frontend checks before publishing.

Put owned images in `frontend/static/images/`, then set `heroImage` or `storyImage` to `/images/your-image.webp`. Provide meaningful `heroAlt` and `storyAlt` text. The current remote placeholders can be replaced without touching application logic. Guest uploads are separate and remain private in S3.

`frontend/src/app.css` contains the shared colours, typography and responsive styles. `frontend/src/lib/components/` contains the small presentation sections. `backend/app/templates/invitation.html` controls the responsive email layout; its text comes from this JSON and all inserted guest values are escaped.

Changing JSON or assets requires rebuilding/redeploying. Never put real guest lists, private photos, invitation tokens or secrets in this public directory.

## English and Italian

- `locales/en/wedding.json`: shared names, date/time, image paths, venue and English story, schedule and FAQs.
- `locales/it/wedding.json`: Italian overrides for the story, schedule, FAQs, dates and image descriptions. Shared values such as image URLs and names are inherited, so change them only once.
- `locales/en/ui.json` and `locales/it/ui.json`: all interface wording, including navigation, RSVP, photo sharing and the invitation administration page. Keep the keys identical; edit the values. Preserve placeholders such as `{count}` and `{name}`.

The language switch remembers a visitor’s choice on that device. On a first visit, an Italian browser defaults to Italian; other browsers default to English. Language selection never reloads the page or clears an RSVP form. The HTML language changes for screen readers. Original guest names, messages and captions are never machine-translated.

The landing page uses lightweight CSS and one IntersectionObserver for entrance animations. Reduced-motion visitors see the same content without animation. Change the visual styling in `frontend/src/app.css`; no animation library is needed.

Run `npm --prefix frontend run check` to check translation keys, interpolation placeholders and schedule consistency as well as Svelte/TypeScript. `tests/browser/languages.spec.ts` covers language switching, saved preferences, Italian RSVP, admin localisation and reduced motion on desktop and mobile. Docker browser tests connect directly to Floci using Chromium’s hostname mapping, preserving the original multipart photo upload bytes.

## Venue, travel, hotel and Akamaru

The `travel` and `dog` objects in each wedding JSON file contain these sections. Venue images live in `frontend/static/images/`. Replace `dog.image` with Akamaru’s real photo when ready. Update both languages when the hotel and ceremony timings are confirmed; set `scheduleUnconfirmed` to `false` and replace each schedule `time` with its confirmed time. The countdown currently targets the start of the wedding day in Europe/Rome, not a guessed ceremony time. See `ASSETS.md` for image provenance and travel sources.
