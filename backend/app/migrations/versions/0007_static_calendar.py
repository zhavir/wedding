"""Remove the redundant calendar payload from the confirmation email outbox."""

import sqlalchemy as sa
from alembic import context, op

revision = "0007_static_calendar"
down_revision = "0006_guest_language"
branch_labels = None
depends_on = None


def upgrade():
    db = op.get_bind()
    columns = (
        {"calendar"}
        if context.is_offline_mode()
        else {column["name"] for column in sa.inspect(db).get_columns("confirmation_emails")}
    )
    if "calendar" in columns:
        with op.get_context().autocommit_block():
            op.drop_column("confirmation_emails", "calendar")


def downgrade():
    raise RuntimeError(
        "Static calendar attachments are forward-only; restore a backup to downgrade."
    )
