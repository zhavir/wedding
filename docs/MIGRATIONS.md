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

The script upgrades, compares SQLAlchemy metadata, repeats the upgrade, verifies seed counts, then drops only the database it created. Revision 0004 is forward-only. It refuses DSQL. Do not run downgrade against real wedding data. Before future releases, back up the database and test revisions against the local PostgreSQL stack.

Revision `0004_guests_and_invitations` creates Guests and photo-to-guest targeting, adds response fields and a guest relationship to Invitations, normalizes optional unique invitation emails, migrates existing response details, and seeds Italian/English +1, bride and groom copy. It removes the old response, attendee, witness-response, message-selection and section-copy tables. Authentication, notification and confirmation-delivery tables remain.

The migration is forward-only: use a backup to restore the old schema. DSQL DDL uses separate autocommit blocks. Columns are added nullable with defaults set separately. Unique guest/email indexes use `CREATE UNIQUE INDEX ASYNC` and the online migration waits for each job. Offline DSQL SQL includes explicit instructions to wait for the returned index job IDs before application startup. It can be generated without AWS access, but does not prove a live DSQL upgrade succeeded.

`0003_carousel_visibility` separates gallery publication from carousel selection; the gallery flag still maps to the `published` column. Revision 0004 applies guest targets to both surfaces.

The baseline seeds the bride and groom without sending email. Existing invitation links and media storage paths are preserved. Template layout lives in `backend/app/templates/invitation_en.html` and `invitation_it.html`; mutable wording lives in `invitation_messages`.

### Recovering a failed revision 0004

Older local databases can contain multiple invitations with the same email, including case-only differences. Revision 0004 now checks for these before changing the schema and reports the number of conflicting groups. Resolve each address explicitly: keep it on the intended invitation and make the other invitations link-only (empty string before this revision, `NULL` once the email column is nullable), or reset a disposable local database only if its data is not needed. The migration does not delete or merge guest records automatically.

Revision 0004 can resume after its DDL has partially committed. It recognizes existing tables, columns, indexes and template seeds, copies responses only for invitations that have not been migrated, and skips legacy tables already removed. After resolving duplicate addresses, rerun `docker compose up --build -d --wait web`; do not manually stamp the revision as complete. Offline SQL output is for fresh execution; use the online runner for recovery.

## Guest email ownership (0005)

Revision `0005_guest_email` adds nullable `guests.email`, copies and normalizes each invitation address, creates a unique guest-email index, and only then drops the old index and `invitations.email`. Guest and invitation IDs, tokens, relationships and RSVP response snapshots are preserved. Name-only guests remain valid. No earlier revision is rewritten.

The migration can resume after committed steps. It refuses to remove the old column if any nonempty address cannot be matched to the guest. DSQL uses separate DDL transactions and waits for the asynchronous unique-index build. See [AWS ALTER TABLE support](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/alter-table-syntax-support.html).

This is a coordinated application/schema update: the old application requires `invitations.email`, while the new application requires `guests.email`. Pause guest/admin writes during the production cutover, verify a recoverable backup, apply the migration with the matching application release, and resume traffic after health and invitation/email checks. Do not roll back only the application across this schema boundary. No production migration is performed by local testing.
