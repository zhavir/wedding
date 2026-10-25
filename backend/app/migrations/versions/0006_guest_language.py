"""Move language preferences to guests, preserving existing invitations."""

import sqlalchemy as sa
from alembic import context, op

revision = "0006_guest_language"
down_revision = "0005_guest_email"
branch_labels = None
depends_on = None


def upgrade():
    db = op.get_bind()
    offline = context.is_offline_mode()
    dsql = db.dialect.name == "auroradsql"
    guests = set() if offline else {c["name"] for c in sa.inspect(db).get_columns("guests")}
    invitations = (
        {"language"} if offline else {c["name"] for c in sa.inspect(db).get_columns("invitations")}
    )
    messages = (
        set() if offline else {c["name"] for c in sa.inspect(db).get_columns("invitation_messages")}
    )
    if "plural_text" not in messages:
        with op.get_context().autocommit_block():
            op.add_column(
                "invitation_messages",
                sa.Column(
                    "plural_text", sa.Text, nullable=dsql, server_default=None if dsql else ""
                ),
            )
        op.execute(
            sa.text("UPDATE invitation_messages SET plural_text = text WHERE language = 'en'")
        )
    op.execute(sa.text("UPDATE invitation_messages SET plural_text = '' WHERE plural_text IS NULL"))
    if "language" not in guests:
        with op.get_context().autocommit_block():
            op.add_column(
                "guests",
                sa.Column(
                    "language", sa.String(2), nullable=dsql, server_default=None if dsql else "en"
                ),
            )
    op.execute(sa.text("UPDATE guests SET language = 'en' WHERE language IS NULL"))
    if "language" in invitations:
        op.execute(
            sa.text("""UPDATE guests SET language = (
            SELECT language FROM invitations WHERE guest_id = guests.id
        ) WHERE EXISTS (SELECT 1 FROM invitations WHERE guest_id = guests.id)""")
        )
        with op.get_context().autocommit_block():
            op.drop_column("invitations", "language")


def downgrade():
    raise RuntimeError("Guest language ownership is forward-only; restore a backup to downgrade.")
