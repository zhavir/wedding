# Alembic migrations

Schema revisions live in `backend/app/migrations/versions`:

1. `0001_initial`: initial application tables.
2. `0002_messages`: editable invitation message pools, persisted selected wording, and ten English/Italian guest/witness defaults.
3. `0003_media`: private-by-default publication state and paired Live Photo metadata. Existing uploads are unpublished until reviewed.
4. `0004_rsvp_mfa_metadata`: removes legacy RSVP JSON storage, retains normalized response tables, adds encrypted admin authenticator enrollment and replay protection, and records upload provenance and media metadata.

Local startup runs `python -m app.manage migrate`, then local-only demo seeding. The same operator command is used by the release workflow with the DSQL admin role. Application requests never run migrations.

```sh
docker compose run --rm api python -m app.manage migrate
uv run --frozen --package wedding-api alembic current
uv run --frozen --package wedding-api alembic revision --autogenerate -m 'describe change'
```

Review generated revisions. DSQL permits only one DDL statement per transaction, so DDL uses individual Alembic autocommit blocks. Keep data changes transactional, and plan recovery from partially applied DDL. The baseline tolerates existing pre-release tables; schema drift is detected by validation rather than silently repaired.

Test the complete migration cycle against a newly created, randomly named local PostgreSQL database:

```sh
docker compose run --rm api python scripts/check_migrations.py
```

The script upgrades, compares SQLAlchemy metadata, downgrades to base, upgrades again, verifies seed counts, then drops only the database it created. It refuses DSQL. Do not run downgrade against real wedding data. Before future releases, back up the database and test revisions against the local PostgreSQL stack.

In **Invitation messages**, administrators can create, edit, deactivate and remove English/Italian wording separately for guests and witnesses. Allowed placeholders are `{name}`, `{couple}`, `{date}`, `{venue}`; text is HTML-escaped when rendered. A random matching message is saved per invitation/language/type, so preview and delivery agree. Editing a pool affects future selections, not saved wording. If no active matching message exists, the localized editable default in `content/locales/<language>/wedding.json` is used.

Revision `0005_additional_guests` adds parent invitation links, structured additional-guest emails, and the per-uploader S3 prefix. Existing flat-layout media remains accessible. Run the normal upgrade before starting the updated API (Docker Compose's init service does this automatically).

`0006_wedding_hosts` seeds the bride and groom as ordinary active invitations without sending emails or embedding access secrets. `0007_large_media` adds multipart upload state and upgrades media size/duration fields to 64-bit integers. Fresh databases and upgrades from the previous local schema are supported.
