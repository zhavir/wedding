# Alembic migrations

Schema revisions live in `backend/app/migrations/versions`. The consolidated
`0001_initial` baseline includes the application tables, invitation message defaults,
media metadata, administrator MFA, and wedding host invitations.

When `DSQL_HOST` is set, both the application and Alembic use
`aurora-dsql-sqlalchemy` with the AWS psycopg connector. The connector obtains IAM
tokens for `DB_USER` in `AWS_REGION`; connections verify the server certificate
and hostname using system CA certificates. No database password is configured.
Local `DATABASE_URL` connections retain their configured dialect
(PostgreSQL/asyncpg by default).

The upstream DSQL adapter currently exposes synchronous drivers. The bridge in
`backend/app/db/dsql.py` combines its compiler and reflection behavior with
SQLAlchemy's async psycopg adapter and commits DDL through the async connection
proxy. It also supplies the collation field required by SQLAlchemy 2.1's reflection
reader, which the adapter's older query omits. Keep the async dialect selection,
DDL, and reflection tests when upgrading the adapter.
Alembic registers `auroradsql` as a PostgreSQL-derived implementation with
nontransactional DDL. Offline SQL generation selects the same configured dialect:

```sh
DSQL_HOST=your-cluster.dsql.eu-central-1.on.aws DB_USER=admin uv run --frozen --package wedding-api alembic upgrade head --sql
```

Offline generation does not connect to AWS or obtain IAM credentials.

Local startup runs `python -m app.manage migrate`, then local-only demo seeding. SST invokes the same migration function through a private bootstrap Lambda using the DSQL admin role during deployment. Application requests never run migrations.

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

The baseline seeds the bride and groom as ordinary active invitations without
sending emails or embedding access secrets. It also includes multipart upload
state and 64-bit media size/duration fields.
