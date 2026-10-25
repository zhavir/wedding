# Validation status

## 2026-10-25 — rebuilt stack and completed regression verification

- `docker compose up --build -d --wait web` completed successfully. Init exited successfully; database, API, local AWS emulator and web became healthy. This resolves the earlier approval-limit verification blocker.
- **122 backend tests passed** in the Docker test image, including video processing and the guest-email migration tests.
- The complete browser run passed **74 of 76 tests**. Both failures were the same obsolete favicon assertion on desktop/mobile: without `PUBLIC_ASSET_URL`, the site intentionally omits the S3 favicon. Moved favicon expectations to the asset checks, covering configured asset URLs and unconfigured local placeholders. The affected experience/media suite then passed **20 of 20 tests**, including both previously failing tests. The entire suite was not repeated after this test-only correction.
- Browser verification used local PostgreSQL, the AWS emulator and local picture/video fixtures. No production deployment, production migration, live S3 changes or real email delivery occurred. Diff whitespace checks and discovery of all 76 browser tests passed.

## 2026-10-25 — guest email ownership and asset/layout cleanup

- Email now belongs to Guest. Migration `0005_guest_email` preserves existing addresses and invitation identities before removing the Invitation email column. Guest email edits reset invitation delivery status; recovery, sending and additional-guest matching use the guest address.
- API/init Docker images built successfully. A disposable PostgreSQL check passed fresh upgrade, schema parity, repeated upgrade and seed checks. Targeted backend reruns passed after fixing the migration test transaction; the final migration-preservation and existing-guest/+1 tests both passed. A complete backend suite has not been rerun since those fixes.
- **20 desktop/mobile Playwright checks passed** against local Vite with mocked API and image responses, covering responsive layouts, envelopes, named assets and carousel proportions. Frontend checks, build, lint and formatting, plus Python Ruff/type checks passed.
- Website photographs and favicon use configured S3 assets. Test-only `tests/browser/memory.png` and `memory.mp4` remain local; preview responses use the local PNG as a data URL. After restoring the PNG fixture, its loader passed and Playwright discovered all **76 tests**; browser execution was not repeated for this fixture-only adjustment.
- The final local `docker compose up --build -d --wait web` was not executed because automatic approval review reached its usage limit. The running local stack has not been verified against the new schema. No production migration, deployment, S3 modification or real email delivery was performed.

## 2026-10-24 — configurable photographs and gallery deletion

- All landing photographs now use named objects under `PUBLIC_ASSET_URL`. Story captions and image names are configured per chapter and language; existing ceremony captions remain in section content and guest captions in Gallery admin. See `docs/ASSETS.md` for the complete object-name list.
- Carousel APIs return dimensions and orientation; the frontend preserves image proportions without cropping. Gallery deletion cleans up S3 objects, unfinished multipart uploads and guest assignments.
- **6 targeted Playwright checks passed** on desktop/mobile Chromium against a local Vite server with mocked API/image responses. Coverage includes portrait/landscape/square rendering, named asset URLs, singular/plural Italian seats, equal expanded-header insets with and without animation, and existing responsive chapter layout.
- Backend: **117 passed, 2 failed**. Both failures occur because local `ffmpeg` is missing, before video/Live Photo processing can be tested. New orientation and admin deletion checks passed using SQLite and mocked AWS, including storage cleanup failure and unauthenticated access.
- Frontend checks/build/lint, Python Ruff/type checks and diff whitespace checks passed. No deployment, live S3 upload/deletion, production data changes or email delivery was performed. Existing reference photos must be uploaded to the documented LandingImages keys before releasing the frontend if they are not already present.

## 2026-10-24 — complete desktop/mobile E2E regression

- **72 of 72 Playwright tests passed** (36 desktop, 36 mobile; 3.6 minutes) against the existing local Docker stack with PostgreSQL and Floci. No tests were skipped.
- Updated language, opening, map and upload-link assertions to match the current website copy. The Akamaru check selects the photograph by its accessible name instead of relying on image order.
- Witness and party-host fixtures now use unique email addresses, preventing duplicate-invitation conflicts across projects and repeated runs. Invitation-creation assertions include the response body when they fail.
- Validation covered real local uploads, admin moderation, gallery access, RSVP persistence, additional-guest revocation, translations and responsive presentation. Existing local volumes were preserved; production was not contacted.

## 2026-10-24 — rebuilt Docker stack and admin browser verification

- Rebuilt and started the local stack with `docker compose up --build -d --wait web`. Init completed successfully; PostgreSQL, Floci, API and web became healthy. Existing local database and media volumes were preserved.
- **12 SQLAdmin browser checks passed** on desktop/mobile against the rebuilt stack. They cover guest-first invitation creation, link-only invitations, email preview and sending through Floci, template editing, gallery publication/unpublication, video and Live Photo uploads/playback.
- The image-detail test now checks both visibility fields are actual checkboxes, saves both enabled with a selected guest, reloads to verify persistence, then unchecks all three and verifies they stay cleared after saving.
- These checks used local PostgreSQL, Floci and temporary test administrator credentials. No production deployment, production database changes or real email sending occurred.

## 2026-10-24 — final presentation and admin cleanup

- **26 Playwright checks passed** on desktop/mobile Chromium for envelope growth/open/reversal, fixed invitation sizing, symmetric fold borders, cue spacing, reduced motion, navigation, timeline and immediate gallery/carousel rendering after authentication. Six additional landing-content checks passed in the preceding run.
- **20 targeted backend checks passed**, including reversible gallery/carousel checkboxes, guest checkbox selection/clearing, both bulk visibility actions and migration recovery. These use disposable databases and mocked AWS; no production data was changed.
- Frontend translation/Svelte checks and production build, Python Ruff/format/type checks and whitespace checks passed. Generated SST declarations are excluded from ESLint; application sources remain linted.
- Desktop and mobile envelope screenshots were reviewed. The local init container has exited successfully and the current API/web containers report healthy. This is a read-only status observation, not a claim that those running images include every checkout change.
- Production is already released. This work did not deploy, reset production data or alter production infrastructure. ASSETS.md now distinguishes exact public S3 slots from bundled images; PUBLISH.md separates normal updates from initial setup.

## 2026-10-24 — init migration recovery

- Reproduced the existing init failure from PostgreSQL logs: duplicate emails prevented `uq_invitation_email` creation after earlier migration DDL committed.
- Init and API Docker images rebuilt successfully. A disposable PostgreSQL database passed fresh upgrade, metadata parity, repeated upgrade and seed checks.
- All 14 database tests passed, including duplicate rejection before schema changes and recovery from interruptions during index creation and legacy table removal. Ruff and Python type checks passed.
- At the time of this recovery run, existing duplicates required explicit resolution; no reset or guest-data merge was performed by the agent. A later read-only check found init completed successfully and the local stack healthy (see latest validation above).

## 2026-10-24 — guest and invitation simplification

- Backend: **104 passed, 2 deselected** with disposable SQLite databases and mocked AWS. The two video/Live Photo checks require ffmpeg/ffprobe, which are unavailable in this environment.
- Migration coverage includes schema parity, response preservation, template seeds and offline Aurora DSQL SQL generation. No live DSQL migration was run.
- **14 focused Playwright checks passed** on desktop/mobile for the envelope, shared SVG monogram, story layout, ceremony image stacking and authenticated carousel. Updated SQLAdmin browser scenarios load successfully but were not rerun end-to-end without the Docker test account.
- Frontend checks and production build passed. Python Ruff, formatting and type checks passed; ESLint retains the existing generated-file warning.
- No deployment or live SES delivery was performed. RSVP notifications use the configured `RSVP_NOTIFICATION_EMAIL` recipient.

## 2026-10-23 — envelope, story chapters and private photo feeds

- The backend suite passed 99 tests using disposable SQLite databases and mocked AWS. It covers authenticated carousel access, image-only sampling, all four gallery/carousel visibility combinations, migration parity and preservation of existing gallery approvals. An additional admin-form check passed, saving all four visibility combinations through SQLAdmin (100 backend tests total).
- All 28 browser checks passed against the production build on desktop and mobile Chromium. Coverage includes envelope growth/opening/release/reversal/skip, reduced motion, a single authenticated carousel request, immediate removal on logout, invitation and gallery email destinations, three story chapters/six Polaroids, alternating timeline layout/highlighting, section petals, Akamaru comparison and real calendar downloads from the disposable local API.
- Frontend translation/Svelte checks, production build, Python Ruff/type checks and infrastructure TypeScript passed. ESLint has no errors and retains one existing warning in generated `frontend/src/sst-env.d.ts`.
- Five supplied photographs are bundled WebP assets, including Villa Valentina. Desktop envelope frames were visually reviewed; the flap lining now passes behind the emerging invitation.
- No deployment, GitHub push, live AWS bucket-policy verification or real email delivery was performed. Guest photos remain in the private bucket; both feeds require authentication to obtain expiring signed URLs. The optional public bucket is for editorial landing-page assets only. See [asset instructions](docs/ASSETS.md).

Updated 19 October 2026. Phase 1 was completed before migration/gallery/release changes; final checks cover those changes and the subsequent media moderation requirement.

## Passed locally

- **60 backend tests** in Docker: authentication, QR/TOTP enrollment and replay protection, production rejection of legacy admin tokens, additional invitation email/revocation lifecycle, admin permissions, structured RSVP, witness responses, confirmation/calendar and host notification delivery, duplicate-submit prevention, localized message selection and stable preview/delivery, couple guest seed access, large multipart request validation, long-duration video acceptance, upload validation, byte-preserved originals, real video/HEIC processing, Live Photo pairs, upload metadata and unpublished media filtering. Five offline GitHub ruleset synchronization tests cover idempotence, authorization validation and failed-write protection.
- **40 Playwright tests** on desktop Chromium and mobile Chromium: responsive bilingual landing/form flows, saved-response editing and fresh-code entry, single-picker previews, drag/drop and mixed image/video bulk upload, additional guest invitation and cancellation, mobile gallery navigation, SQLAdmin invitation/message CRUD, admin publication/unpublication, uploader names and filtering, detail image loading and bulk approval, explicit gallery pagination and Load all, retry handling, keyboard/swipe lightbox navigation across page boundaries, focus restoration, real S3 video/Live Photo uploads and video metadata playback.
- PostgreSQL + Floci integration: RSVP persistence, authenticated gallery access, direct private S3 upload, original-byte integrity, WebP previews and pagination. A real 65 MiB multipart MP4 upload also verifies S3 range inspection, server-side original preservation and its WebP poster.
- Fresh PostgreSQL migration cycle: upgrade, model/schema comparison, downgrade to base, re-upgrade, repeated upgrade and ten seeded message records and two active, non-admin bride/groom invitations. The disposable database is removed after validation.
- Full prek hook execution in an isolated Docker checkout: GitHub configuration validation, Ruff lint and formatting, ty, pyproject-fmt, frontend lint/format/types and whitespace checks. These checks are configured in `.pre-commit-config.yaml`.
- Frontend Prettier, translation checks, ESLint, Svelte/TypeScript and production static build.
- SST provider installation and TypeScript infrastructure check; GitHub workflow validation with actionlint 1.7.12. GitHub Actions are pinned to verified current release commits.
- Production Lambda container build without publishing; Docker Compose full stack builds and starts healthy.

## Reproduce

```sh
docker compose up --build -d --wait web
docker compose --profile test run --build --rm unit
docker compose --profile test run --build --rm browser
docker compose --profile test run --build --rm integration
docker compose run --rm api python scripts/check_migrations.py
docker compose --profile test run --rm unit sh -c 'ruff check backend scripts && ruff format --check backend scripts && ty check && pyproject-fmt --check pyproject.toml backend/pyproject.toml'
npm --prefix frontend run format:check
npm --prefix frontend run lint
npm --prefix frontend run check
npm run build
npx sst install
npx tsc -p tsconfig.infra.json
docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:1.7.12
docker build --target lambda -f backend/Dockerfile -t wedding-lambda:check .
```

Tests use local demo invitations and isolated administrator credentials. The local-only browser setup resets the demo upload allowance and proxy throttle counters and creates isolated TOTP-enabled admin accounts. It refuses DSQL, secure-cookie mode and non-Floci AWS endpoints.

## Not claimed as verified

No production deployment, real SES inbox delivery, live Aurora DSQL execution, or AWS IAM policy enforcement was tested. Floci simulates S3/SES and local PostgreSQL exercises SQL semantics; neither proves DSQL service compatibility. Verify live AWS behavior after the approved production deployment and before inviting guests. Native iOS Safari was not available; mobile tests use Chromium with iPhone viewport/touch emulation. MOV/HEVC playback is device-dependent; originals can always be downloaded.

GitHub Actions were validated locally, not executed on GitHub. Repository settings were not changed remotely; synchronization workflows require explicit owner configuration and authorization. See [AWS deployment](docs/DEPLOYMENT.md), [GitHub settings](docs/GITHUB.md), [email setup](docs/EMAIL.md) and [media limitations](docs/MEDIA.md).
