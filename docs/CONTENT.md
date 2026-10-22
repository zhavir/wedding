# Content ownership

Edit the copy in the app that presents it. Each app owns the event details it uses; neither imports content from the other app. Keep private guest data out of all content files.

- `frontend/src/lib/locales/en/ui.json` and `it/ui.json`: interface labels, form wording, navigation, and accessibility text. Keep translation keys and `{placeholders}` aligned.
- `frontend/src/lib/locales/en/content.json` and `it/content.json`: story, schedule, FAQs, travel, Akamaru, image paths/descriptions, and localized display dates. Italian copy inherits shared frontend values from English where omitted.
- `backend/app/locales/en.json` and `it.json`: invitation, witness, and confirmation email text, including template labels and the event details used by emails and calendar attachments. These files ship inside the Python app; they are never imported by the browser.
- `backend/app/templates/email_base.html`: shared, responsive email stationery. `invitation.html` and `confirmation.html` supply their specific copy and actions. Templates autoescape guest data. Optional CSS animations enhance supporting clients; all content and links work without animation.

When changing the date, names, venue, or contact address, update both apps. Keep localized display dates consistent with the machine-readable date. Changing content requires a rebuild. Images belong in `frontend/static/images/`; see [asset notes](ASSETS.md).

## Motion and interaction

`frontend/src/experience.css` contains the linen, sage, and ribbon styling. `Opening.svelte` opens the mockup-inspired linen curtains and loosens the gold ornament with scroll or its button. `BotanicalFrame.svelte` restores the moving side flowers on desktop and keeps them at the opening/footer edges on mobile. `Timeline.svelte` follows the SVG curve with scroll and reveals decorative keepsakes. `Footer.svelte` ties the gold ornament when it enters view. `Countdown.svelte` joins the wedding rings as it enters view. `ChapterNav.svelte` provides a single expanding chapter dock with inert hidden links and Escape-key dismissal. The landing and gallery pages share `SiteHeader.svelte`; the gallery retains its back link and sign-out action. `Menu.svelte` displays clearly provisional menu copy from each frontend locale. No third-party animation runtime is required.

Reduced-motion visitors get a fully open invitation, visible timeline content, and static decorations. Flowers do not cover mobile content. Hover details are decorative; touch and keyboard users retain every action. RSVP submission acknowledges the adjacent data-use notice without a separate checkbox; witnesses still explicitly accept their role.

The Cormorant Garamond and DM Sans fonts are self-hosted under `frontend/static/fonts/`, with their OFL licenses. The monogram favicon is `frontend/static/favicon.svg`.

The language switch preserves input and remembers the visitor's choice. English is the fallback for browsers other than Italian. Guest names, messages, and captions are never machine-translated.

## Checks

Run `npm --prefix frontend run check` for locale parity and Svelte types, `npm --prefix frontend run build`, and the backend and browser suites. Browser coverage includes mobile navigation, scroll animation, reduced motion, English/Italian switching, RSVP, witnesses, admin, and private media uploads.

The invitation’s “Save the date” link downloads `/api/calendar.ics` in the selected language. It reuses the confirmation email’s calendar generator and stable event UID. The event is all-day until ceremony times are confirmed; its date, venue and description come from the backend locale files.
