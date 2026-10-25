# Editing the wedding copy

Runtime translations live in `frontend/src/lib/locales/{en,it}/`:

- `content/event.json`: couple, date, venue, RSVP deadline and contact details.
- `content/story.json`, `timeline.json`, `questions.json`, `travel.json`, `akamaru.json`, `ceremony-visions.json`, `footer.json`: one section per file, matching keys in both languages.
- `ui/<component>.json`: short interface labels grouped by the component that uses them. `shared.json` contains reused labels; `api-errors.json` contains API error translations.

Keep the same keys and placeholders in both languages. `npm run check` checks section parity, interpolation placeholders and matching timeline times. Do not add `N/A`: remove the unused copy and its rendering instead.

Confirmed details: 20 May 2027, arrival 16:00, ceremony 16:30, aperitivo 17:00, dinner 19:00, cake 21:00, final drinks and goodbyes 22:00–00:00. RSVP deadline: 30 April 2027. The uploaded files do not specify a separate catering appointment date.

`CeremonyVisions.svelte` replaces the old menu section. `OurStory.svelte` reserves three story chapters with two Polaroid frames each; every image name and caption is configurable in the chapter’s `photos` array. `Akamaru.svelte` provides a pointer/touch/keyboard comparison slider. The timeline uses compact text entries with the closest entry highlighted as the scroll marker moves. The original section-scoped petal isolation is preserved, so no chapter petals spill over the opening invitation. See [ASSETS.md](ASSETS.md) for photography and WebP conversion.

## Admin-owned email copy

Invitation layouts are code-owned Jinja templates, `backend/app/templates/invitation_en.html` and `invitation_it.html`, using shared stationery. Static email labels and event facts live in `backend/app/services/email_content.py`. There are no runtime backend locale files or section-copy database records.

**Invitation Email Template** stores mutable text by language and audience (guest, witness, groom, bride, +1). Supported placeholders are `{name}`, `{couple}`, `{date}`, `{venue}`. Previews and sends use the first active template by ID matching language/audience; edits take effect immediately. Static code-owned introductory text is the fallback when no matching template exists.

## Authenticated photo carousel

The landing page makes one asynchronous request to `/api/photos/carousel` per authenticated session. It never requests photos before authentication and clears them on logout. The static page renders independently of that request. All distinct, completed still photos with **Visible in carousel** enabled are returned; videos are excluded. Photos with guest targets are visible only to those guests, in both the carousel and gallery. Responses contain IDs, captions, dimensions, orientation and temporary signed previews; originals stay private.

**Visible in gallery** and **Visible in carousel** are independent controls: both, either, or neither can be enabled. Both API feeds require a valid invitation session. Empty/error responses leave the page usable. Motion pauses on hover; reduced-motion users can scroll manually. The carousel does not poll or refresh expired URLs.

## Envelope opening

`EnvelopeOpening.svelte` uses a pinned scroll scene. The closed envelope enlarges, the flap opens, and the invitation stays at its final viewport size while the envelope moves down. Scroll reversal reverses these transforms continuously. The animated **Scroll to reveal** cue can be clicked to reveal the invitation; reduced motion shows it immediately.

## Layout conventions

Use Tailwind utilities for grids, flex layout, widths, gaps, padding and responsive switches. Story chapters, ceremony figures, photo placeholders and the carousel share this approach; their semantic classes remain available for animation and browser checks. Existing 600/700px layout thresholds use explicit Tailwind breakpoints to retain the reviewed proportions.

Keep custom CSS for envelope geometry, timeline paths, Polaroid rotation, fonts and decorative effects. Remove the corresponding CSS rule when moving layout to utilities: unlayered legacy CSS otherwise takes precedence over Tailwind's utility layer. Production images use S3 exclusively; tests use local picture and video fixtures in `tests/browser/` for uploads and previews, without fetching media from S3.
