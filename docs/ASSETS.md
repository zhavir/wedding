# Photography and source information

Wedding details: Andrea and Sara, 20 May 2027. Ceremony times, RSVP deadline, parking arrangements and partner hotel details are deliberately unconfirmed placeholders.

Venue address and description were checked against:
- https://www.villa-valentina.it/contatti.php
- https://www.villa-valentina.it/lavilla.php

Local WebP assets are resized versions of photographs from the venue’s official website, fetched for this site at the couple’s request:
- `venue-exterior.webp`: https://www.villa-valentina.it/img/explore1.jpg (floral ceremony seating)
- `venue-garden.webp`: https://www.villa-valentina.it/img/explore2.jpg (carriage outside the villa)
- `venue-interior.webp`: https://www.villa-valentina.it/img/villa.jpg (interior)

These third-party photographs retain their original owners’ rights; the repository’s MIT licence covers the code, not those photographs. Keep the venue’s permission for publication with your wedding records. Replace image paths in `frontend/src/lib/locales/en/content.json` when using your own photographs.

Train information: https://www.trenord.it/linee-e-orari/circolazione/le-nostre-linee/varese-saronno-milano/?code=R22

The guidance identifies Tradate station and recommends arranging the final taxi/lift in advance. It does not promise a walking distance, train time, shuttle, parking availability or future timetable. The embedded map loads only after the guest requests it.

`akamaru-placeholder.svg` is an original editable dachshund illustration, explicitly marked as a placeholder. It is not a photograph of Akamaru. The Instagram link is https://www.instagram.com/akamaru_theminisausage/; no Instagram images were downloaded. Change `dog.image` and `dog.imageAlt` in both content files when his real photo is available.

## Typography and decorative graphics

The supplied Animated Wedding UI mockup informed the curtain, monogram, botanical border, rings, and editorial layout. Cormorant Garamond and DM Sans are self-hosted in `frontend/static/fonts/`; their SIL Open Font License files are included alongside them. Guests do not contact Google Fonts. Botanical decorations, the gold ornament, place setting, and favicon use local SVG/CSS.

The layered curtain treatment is independently implemented in Svelte/SVG/CSS, using Ri8x’s [Curtains (Flex)](https://codepen.io/Ri8x/pen/jOqopKG) as a motion reference: gathered panels and shaded pleats, with a curved hem that opens ahead of the top. No external scripts or assets from the pen are loaded.
