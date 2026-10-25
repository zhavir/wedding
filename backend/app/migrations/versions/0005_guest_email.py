"""Move contact email to guest identity without changing invitation credentials."""

import sqlalchemy as sa
from alembic import context, op

revision = "0005_guest_email"
down_revision = "0004_guests_and_invitations"
branch_labels = None
depends_on = None


def upgrade():
    db = op.get_bind()
    offline = context.is_offline_mode()
    guest_columns = set() if offline else {c["name"] for c in sa.inspect(db).get_columns("guests")}
    invitation_columns = (
        {"email"} if offline else {c["name"] for c in sa.inspect(db).get_columns("invitations")}
    )
    if "email" not in guest_columns:
        with op.get_context().autocommit_block():
            op.add_column("guests", sa.Column("email", sa.String(254), nullable=True))
    if "email" in invitation_columns:
        op.execute(
            sa.text("""UPDATE guests SET email=(
            SELECT NULLIF(lower(email), '') FROM invitations WHERE guest_id=guests.id
        ) WHERE email IS NULL AND EXISTS (
            SELECT 1 FROM invitations WHERE guest_id=guests.id
        )""")
        )
        if not offline and db.scalar(
            sa.text("""SELECT count(*) FROM invitations i
            LEFT JOIN guests g ON g.id=i.guest_id
            WHERE NULLIF(i.email, '') IS NOT NULL
            AND (g.id IS NULL OR g.email IS NULL OR g.email <> lower(i.email))""")
        ):
            raise RuntimeError(
                "Guest email migration could not preserve every address; no invitation email column was removed."
            )
    indexes = set() if offline else {i["name"] for i in sa.inspect(db).get_indexes("guests")}
    if "uq_guest_email" not in indexes:
        with op.get_context().autocommit_block():
            if db.dialect.name == "auroradsql":
                statement = sa.text("CREATE UNIQUE INDEX ASYNC uq_guest_email ON guests (email)")
                if offline:
                    op.execute(statement)
                    op.execute(
                        sa.text(
                            "-- Wait with SELECT sys.wait_for_job('returned_job_id') before continuing."
                        )
                    )
                else:
                    job = db.execute(statement).scalar_one()
                    if not db.execute(
                        sa.text("SELECT sys.wait_for_job(:job)"), {"job": str(job)}
                    ).scalar_one():
                        raise RuntimeError("Guest email unique index did not complete.")
            else:
                op.create_index("uq_guest_email", "guests", ["email"], unique=True)
    if "email" in invitation_columns:
        indexes = (
            {"uq_invitation_email"}
            if offline
            else {i["name"] for i in sa.inspect(db).get_indexes("invitations")}
        )
        if "uq_invitation_email" in indexes:
            with op.get_context().autocommit_block():
                op.drop_index("uq_invitation_email", table_name="invitations")
        with op.get_context().autocommit_block():
            op.drop_column("invitations", "email")


def downgrade():
    raise RuntimeError("Guest email ownership is forward-only; restore a backup to downgrade.")
