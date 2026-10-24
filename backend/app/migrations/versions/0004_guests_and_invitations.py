"""Guest identities, invitation responses and targeted gallery visibility.

DSQL: DDL statements run separately; added columns are nullable, defaults are
set separately, and unique indexes are built asynchronously before proceeding.
"""

import sqlalchemy as sa
from alembic import context, op

revision = "0004_guests_and_invitations"
down_revision = "0003_carousel_visibility"
branch_labels = None
depends_on = None


COLUMNS = [
    ("guest_id", sa.String(64), None),
    ("attending", sa.Boolean(), None),
    ("message", sa.Text(), ""),
    ("dietary", sa.Text(), ""),
    ("response_email", sa.String(254), ""),
    ("response_guests", sa.Text(), "[]"),
    ("consent", sa.Boolean(), False),
    ("witness_acceptance", sa.Boolean(), False),
    ("updated_at", sa.Integer(), 0),
]


def upgrade():
    db = op.get_bind()
    offline = context.is_offline_mode()
    tables = set() if offline else set(sa.inspect(db).get_table_names())
    columns = set() if offline else {c["name"] for c in sa.inspect(db).get_columns("invitations")}
    indexes = set() if offline else {i["name"] for i in sa.inspect(db).get_indexes("invitations")}
    if not offline:
        duplicates = db.scalar(
            sa.text("""SELECT count(*) FROM (
            SELECT lower(email) FROM invitations
            WHERE email IS NOT NULL AND email <> ''
            GROUP BY lower(email) HAVING count(*) > 1
        ) AS duplicate_emails""")
        )
        if duplicates:
            raise RuntimeError(
                f"Migration 0004 requires unique invitation emails: {duplicates} duplicate groups. "
                "Resolve duplicates before retrying (keep one email per address; use NULL for "
                "link-only invitations). No records have been deleted."
            )
    if "guests" not in tables:
        with op.get_context().autocommit_block():
            op.create_table(
                "guests",
                sa.Column("id", sa.String(64), primary_key=True),
                sa.Column("name", sa.String(100), nullable=False),
                sa.Column("audience", sa.String(10), nullable=False, server_default="guest"),
            )
    if "photo_guests" not in tables:
        with op.get_context().autocommit_block():
            op.create_table(
                "photo_guests",
                sa.Column("photo_id", sa.String(64), primary_key=True),
                sa.Column("guest_id", sa.String(64), primary_key=True),
            )
    for name, kind, default in COLUMNS:
        if name not in columns:
            with op.get_context().autocommit_block():
                op.add_column("invitations", sa.Column(name, kind, nullable=True))
        # SQLite cannot ALTER DEFAULT; service writes all defaults explicitly.
        if default is not None and op.get_bind().dialect.name != "sqlite":
            with op.get_context().autocommit_block():
                op.alter_column(
                    "invitations",
                    name,
                    server_default=sa.text(
                        "false"
                        if default is False
                        else "0"
                        if default == 0
                        else "'" + str(default) + "'"
                    ),
                )
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("invitations") as batch:
            batch.alter_column("email", existing_type=sa.String(254), nullable=True)
    else:
        with op.get_context().autocommit_block():
            op.alter_column("invitations", "email", nullable=True)

    op.execute(
        sa.text("""INSERT INTO guests (id, name, audience)
        SELECT id, name, CASE
          WHEN parent_invitation_id <> '' THEN '+1'
          WHEN id = 'wedding-groom' THEN 'groom'
          WHEN id = 'wedding-bride' THEN 'bride'
          WHEN is_witness THEN 'witness' ELSE 'guest' END
        FROM invitations WHERE NOT EXISTS (SELECT 1 FROM guests WHERE guests.id=invitations.id)""")
    )
    if db.dialect.name == "sqlite":
        people = """json_group_array(CASE WHEN email <> ''
            THEN json_object('name', name, 'dietary', dietary, 'email', email)
            ELSE json_object('name', name, 'dietary', dietary) END ORDER BY position)"""
    else:
        people = """CAST(json_agg(json_strip_nulls(json_build_object(
            'name', name, 'dietary', dietary, 'email', NULLIF(email, '')
        )) ORDER BY position) AS TEXT)"""
    if offline or db.scalar(sa.text("SELECT count(*) FROM invitations WHERE guest_id IS NULL")):
        op.execute(
            sa.text(f"""UPDATE invitations SET guest_id=id, email=NULLIF(lower(email), ''),
        attending=(SELECT attending FROM rsvp_responses WHERE invitation_id=invitations.id),
        message=COALESCE((SELECT message FROM rsvp_responses WHERE invitation_id=invitations.id), ''),
        dietary=COALESCE((SELECT dietary FROM rsvp_guests WHERE invitation_id=invitations.id AND position=0 AND active=true), ''),
        response_email=COALESCE((SELECT email FROM rsvp_responses WHERE invitation_id=invitations.id), ''),
        response_guests=COALESCE((SELECT {people} FROM rsvp_guests WHERE invitation_id=invitations.id AND active=true), '[]'),
        consent=COALESCE((SELECT consent FROM rsvp_responses WHERE invitation_id=invitations.id), false),
        witness_acceptance=COALESCE((SELECT accepted FROM witness_responses WHERE invitation_id=invitations.id), false),
        updated_at=COALESCE((SELECT updated_at FROM rsvp_responses WHERE invitation_id=invitations.id), 0)
        WHERE guest_id IS NULL
    """)
        )
    for language, text in [
        (
            "en",
            "Dear {name}, you are invited to celebrate with us at {venue} on {date}. We cannot wait to welcome you!",
        ),
        (
            "it",
            "Ciao {name}, sei invitato a festeggiare con noi a {venue} il {date}. Non vediamo l’ora di averti con noi!",
        ),
    ]:
        for audience in ("+1", "bride", "groom"):
            table = sa.table(
                "invitation_messages",
                *[sa.column(name, sa.String) for name in ("id", "language", "audience", "text")],
                sa.column("active", sa.Boolean),
            )
            if not offline and db.scalar(
                sa.text("SELECT id FROM invitation_messages WHERE id=:id"),
                {"id": f"default-{language}-{audience}"},
            ):
                continue
            op.execute(
                table.insert().values(
                    id=op.inline_literal(f"default-{language}-{audience}"),
                    language=op.inline_literal(language),
                    audience=op.inline_literal(audience),
                    text=op.inline_literal(text),
                    active=True,
                )
            )
    for column in ("guest_id", "email"):
        name = "uq_invitation_guest" if column == "guest_id" else "uq_invitation_email"
        if name in indexes:
            continue
        with op.get_context().autocommit_block():
            if db.dialect.name == "auroradsql":
                if context.is_offline_mode():
                    op.execute(
                        sa.text(f"CREATE UNIQUE INDEX ASYNC {name} ON invitations ({column})")
                    )
                    op.execute(
                        sa.text(
                            f"-- Wait for the returned job_id using SELECT sys.wait_for_job('job_id') before starting the application ({name})."
                        )
                    )
                    continue
                job = db.execute(
                    sa.text(f"CREATE UNIQUE INDEX ASYNC {name} ON invitations ({column})")
                ).scalar_one()
                if not db.execute(
                    sa.text("SELECT sys.wait_for_job(:job)"), {"job": str(job)}
                ).scalar_one():
                    raise RuntimeError(f"DSQL index build failed: {name}")
            else:
                op.create_index(name, "invitations", [column], unique=True)
    for table in (
        "rsvp_guests",
        "rsvp_responses",
        "witness_responses",
        "invitation_message_choices",
        "email_copy",
    ):
        if offline or table in tables:
            with op.get_context().autocommit_block():
                op.drop_table(table)


def downgrade():
    raise RuntimeError(
        "This consolidation is forward-only; restore a database backup to downgrade."
    )
