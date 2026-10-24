# Website images: production upload guide

The site is already in production. Use the existing **LandingImages** bucket for public editorial photos and **Photos** for private guest uploads. Do not create replacement buckets or change production resource names.

## Find the correct bucket

The application SST outputs are `landingImages` (bucket name), `landingImagesUrl` (HTTPS base URL), and `photos` (private bucket). Use the existing production stack's outputs or identify the `LandingImages` resource in the AWS console. Do not guess a bucket name from the website domain. The build receives `PUBLIC_ASSET_URL` from `landingImagesUrl`.

Only deliberately public website photography belongs in LandingImages. Guests upload through the website into Photos; the backend creates its object names, previews and signed links. Copying a file directly into Photos does not create a Gallery admin record.

## Files to upload to LandingImages

Upload these exact, lowercase object keys at the **bucket root**, without an `images/` directory:

| Object key | Website placement | Recommended crop |
| --- | --- | --- |
| `venue-exterior.webp` | Floral photograph inside the opening invitation | Landscape; keep the subject centered |
| `story-01.webp` | First story chapter, first frame | Portrait 3:4 |
| `story-02.webp` | First story chapter, second frame | Portrait 3:4 |
| `story-03.webp` | Second story chapter, first frame | Portrait 3:4 |
| `story-04.webp` | Second story chapter, second frame | Portrait 3:4 |
| `story-05.webp` | Third story chapter, first frame | Portrait 3:4 |
| `story-06.webp` | Third story chapter, second frame | Portrait 3:4 |

Missing photos show paper placeholders. The frames use `object-fit: cover`, so crop intentionally and keep faces away from the edges.

## Images bundled with the website

These files live in `frontend/static/images/` and take precedence over S3. Uploading another file with the same name to LandingImages will **not** replace them:

| Repository file | Placement |
| --- | --- |
| `villa-valentina.webp` | Travel section; the component's internal slot is `venue-garden` |
| `ceremony-bride.webp` | Bride's imagined ceremony |
| `ceremony-groom.webp` | Groom's imagined ceremony |
| `akamaru.webp` | Real Akamaru, comparison slider |
| `akamaru-naruto.webp` | Naruto namesake, comparison slider |

To replace a bundled picture, replace its repository file and release the frontend. The two Akamaru pictures should use the same 4:5 canvas. `venue-garden.webp`, `venue-interior.webp` and `venue-celebration.webp` are not S3 slots used by the current page.

## Convert and upload

Keep originals under ignored `tmp/source/`, renamed to the stems above. The converter preserves originals, respects orientation, removes metadata including GPS, never upscales and creates WebP files with a default maximum edge of 1600 pixels:

```sh
uv sync --frozen --all-packages --group dev
uv run python scripts/optimize_images.py tmp/source tmp/landing-images
```

Use your existing production AWS profile and replace `YOUR-EXISTING-LANDING-BUCKET` below. Upload only the intended public files; do not run a bucket-wide sync with deletion:

```sh
aws s3 cp tmp/landing-images/venue-exterior.webp s3://YOUR-EXISTING-LANDING-BUCKET/venue-exterior.webp --content-type image/webp --cache-control 'public,max-age=3600'
aws s3 cp tmp/landing-images/story-01.webp s3://YOUR-EXISTING-LANDING-BUCKET/story-01.webp --content-type image/webp --cache-control 'public,max-age=3600'
```

Repeat for `story-02.webp` through `story-06.webp`. No object ACL is needed. Open `LANDING_IMAGES_URL/story-01.webp` directly, then reload the website. Replacing an existing S3 object does not require a frontend release; cached images may remain for up to an hour. If the direct URL works but the page still shows a placeholder, reload the page and check the exact filename and configured asset URL.

For local Docker preview, put `PUBLIC_ASSET_URL=https://YOUR-LANDING-BUCKET-URL` in the root `.env`, then rebuild the web image. For Vite, set that environment variable before `npm --prefix frontend run dev`, or use ignored `frontend/.env.local`. This is a build-time setting; changing it on an already-built frontend requires a rebuild.

## Guest gallery and carousel

Upload guest media through `/gallery#upload`. In **Gallery**, select completed media and use **Make visible in gallery** or **Make visible in carousel**. The flags are independent; the carousel includes still photos only. Open an image's detail page to check or uncheck either flag and individual **Visible to guests** checkboxes, then **Save visibility**. No selected guests means every authenticated guest can see it; otherwise only the selected guest identities can see it in either feed.

Signed URLs grant temporary access to individual private objects. Removing visibility blocks future API results but does not revoke links already issued; those expire after at most one hour. Never put guest originals into LandingImages.

## Sources

- Venue garden/carriage: [Villa Valentina](https://www.villa-valentina.it/img/explore2.jpg).
- Bride’s ceremony: the user-supplied [The Sims wedding image](https://preview.redd.it/where-do-you-throw-your-favorite-weddings-v0-73eccgdb15ib1.jpg?width=1080&crop=smart&auto=webp&s=b4a2c94c7351716f8621fd3f56c81b1429df70c7).
- Groom’s ceremony: [Alpine winter wedding](https://asparklylifeforme.com/wp-content/uploads/2025/10/Alpine-Winter-Wedding-Ceremony-Ideas-4-683x1024.webp).
- Real Akamaru: the user-supplied Instagram CDN photograph, now preserved in `frontend/static/images/akamaru.webp`; [profile](https://www.instagram.com/akamaru_theminisausage/).
- Namesake: [Akamaru from Naruto](https://cdn.anime-planet.com/characters/primary/akamaru-1.webp?t=1726407391).

Third-party photography remains subject to its owners’ rights; the repository’s MIT licence covers code. Cormorant Garamond and DM Sans are self-hosted with their SIL Open Font License files. Botanical decorations, ribbon ornaments and favicon remain local SVG/CSS.
