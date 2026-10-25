# Andrea & Sara · 20 May 2027

An English/Italian wedding website for Villa Valentina in Tradate, with a live countdown, story, event details, travel information, a map, hotel placeholder, Akamaru’s section, private RSVP and an infinite-scroll photo gallery.

The frontend uses SvelteKit, TypeScript and Tailwind. The async FastAPI/Pydantic backend uses SQLAlchemy; local Docker runs PostgreSQL and Floci for S3/SES. SQLAdmin provides the organisers’ administration interface. Python packaging uses `uv_build`; dependencies are locked in `uv.lock` and npm lockfiles.

## Start locally

```sh
docker compose up --build -d --wait
```

Open http://localhost:5173. Use `DEMO-LOVE-2027` as the local guest invitation code. API: http://localhost:8000/api/health. Floci: http://localhost:4566. Docker Desktop should use Linux containers.

The initializer creates missing SQL tables, a photo bucket, upload CORS/lifecycle rules and local invitation records. Named volumes preserve data across restarts. `docker compose down -v` deletes local data permanently.

## Administration

Create an account from your terminal:

```sh
docker compose exec api python -m app.manage admin-user --username andrea
```

Enter and confirm your own password (at least 14 characters), then open **http://localhost:5173/api/admin/**. There is no default admin password. `/admin` redirects to this interface. The old admin email-link login does not authenticate SQLAdmin.

Create a name and optional email in **Guests**, select it and choose **Create invitations**, then edit its invitation and review the private link/email preview. Select invitation records and choose **Actions → Send invitation** to review and confirm delivery separately. See [the admin guide](docs/ADMIN.md) for password resets, bulk sending, session behaviour and production credential provisioning.

## Real email and RSVP notifications

Follow [the SES setup guide](docs/EMAIL.md) to enable real delivery, select an Italian or English invitation template, share a private link without knowing a guest’s email, and configure `RSVP_NOTIFICATION_EMAIL`. Normal Docker uses Floci and sends no real email. The admin menu contains Guests, Invitations, Gallery and Invitation Email Template. RSVP details live on invitations, and +1 emails are sent automatically with admin notifications.

## Edit content and images

See the [content guide](docs/CONTENT.md). Frontend translations are grouped by section/component under `frontend/src/lib/locales/{en,it}/`. Email copy is editable in the admin database. All landing photographs load by name from the SST `LandingImages` bucket; no website image files are bundled in the repository (test picture and video fixtures stay local); see [image names, conversion and upload instructions](docs/ASSETS.md).

The countdown targets 20 May 2027 at 16:30 in Italy; the RSVP deadline is 30 April 2027. Review the contact email and hotel copy before changing published content. Story photography uses six optional S3 slots; the venue, ceremony and Akamaru pictures also load from S3.

## Validation

```sh
# Full local browser flows, including SQLAdmin and a random local test account
docker compose --profile test run --build --rm browser
# API/SQL tests
docker compose --profile test run --build --rm unit
# Real local SQL/S3 integration, including original-byte comparison
docker compose --profile test run --rm integration
```

For host development with the required Node/Python versions:

```sh
uv sync --frozen --all-packages --all-groups
npm ci
npm --prefix frontend ci
uv run --frozen --package wedding-api prek run --all-files
uv run --package wedding-api ruff check backend scripts
uv run --package wedding-api ty check
npm --prefix frontend run check
npm --prefix frontend run lint
npm --prefix frontend run format:check
npm --prefix frontend run build
```

`check` validates translation keys/placeholders and Svelte/TypeScript. Browser tests cover English/Italian preferences, RSVP, admin credentials, record creation, email confirmation, photo upload, phone layouts, reduced motion and hero spacing with enlarged text. Test emails go to Floci, not real recipients.

## Invitation codes and the gallery

The landing page links to **`/gallery#upload`**; the gallery and photo uploader have their own page. Both RSVP and photos accept the personal link or the short code included in the invitation email. An existing guest cookie restores access automatically. Opening an invitation authenticates the guest; they still choose their attendance and submit the RSVP form.

**Lost your code?** sends a replacement only to an email address already registered on an active guest invitation. The response does not reveal whether an address is registered. A replacement must first be used within 15 minutes. Using it replaces the old code and email link; merely requesting one leaves the existing invitation usable. Requests are rate limited, with a five-minute cooldown per invitation. Existing signed-in devices stay signed in.

## Private photos and sessions

Guest email links establish an HttpOnly session cookie. Browsers retain it for up to 400 days and authenticated requests renew it; a browser can still remove cookies. Revoking an invitation blocks its sessions. SQLAdmin uses a separate password login and eight-hour HttpOnly session cookie.

Guests upload original images, videos and paired Live Photos directly to S3. Images support JPEG/PNG/WebP/HEIC/HEIF up to 25 MiB; videos support MP4/MOV/WebM without an application size or duration cap. Large files transfer directly to S3 in parts. Completion validates media and preserves original bytes while producing a small WebP preview. Uploads stay hidden until an administrator publishes them through Gallery. See [media guidance](docs/MEDIA.md) for Live Photo export and playback details. Originals may contain location metadata. Gallery access requires an invitation; downloads use expiring signed URLs. Pending uploads expire after one day. Completed originals are not automatically deleted.

## AWS deployment

The product is already released in production. Use the [production update guide](docs/PUBLISH.md) for subsequent releases and [image upload guide](docs/ASSETS.md) to replace editorial photographs. Keep the existing domain, SST stages, encryption key and storage resources.

The SST configuration provisions same-origin CloudFront routing, a static SvelteKit frontend, FastAPI on Lambda, Aurora DSQL and private S3 media storage. See [deployment and approval setup](docs/DEPLOYMENT.md), [GitHub restrictions](docs/GITHUB.md), [database migrations](docs/MIGRATIONS.md), and [media uploads/moderation](docs/MEDIA.md).

CI builds and tests the application. Releases are manually dispatched by the repository owner and require explicit approval. Local validation does not establish the health of the deployed production version.
