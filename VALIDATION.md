# Validation status

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
