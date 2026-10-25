"""Align database defaults and DSQL-added column nullability with current models.

Preserve existing guest language preferences; Italian is the default for new
records only. Historical revisions remain valid upgrade starting points.
"""

import sqlalchemy as sa
from alembic import op

revision = "0008_align_schema_defaults"
down_revision = "0007_static_calendar"
branch_labels = None
depends_on = None

# Explicit historical values: migrations must not import mutable application models.
DEFAULTS = {
    "guests": [("language", sa.String(2), "it", True)],
    "invitation_messages": [("plural_text", sa.Text(), "", True)],
    "invitations": [
        ("is_witness", sa.Boolean(), sa.false(), False),
        ("message", sa.Text(), "", True),
        ("dietary", sa.Text(), "", True),
        ("response_email", sa.String(254), "", True),
        ("response_guests", sa.Text(), "[]", True),
        ("consent", sa.Boolean(), sa.false(), True),
        ("witness_acceptance", sa.Boolean(), sa.false(), True),
        ("updated_at", sa.Integer(), "0", True),
    ],
    "photos": [("carousel_visible", sa.Boolean(), sa.false(), True)],
}


def upgrade():
    for table, columns in DEFAULTS.items():
        if op.get_bind().dialect.name == "sqlite":
            with op.batch_alter_table(table) as batch:
                for name, kind, default, nullable in columns:
                    batch.alter_column(
                        name, existing_type=kind, server_default=default, nullable=nullable
                    )
            continue
        for name, kind, default, nullable in columns:
            with op.get_context().autocommit_block():
                op.alter_column(table, name, existing_type=kind, server_default=default)
            if table in {"guests", "invitation_messages"}:
                with op.get_context().autocommit_block():
                    op.alter_column(table, name, existing_type=kind, nullable=nullable)


def downgrade():
    raise RuntimeError("Schema default alignment is forward-only; restore a backup to downgrade.")
