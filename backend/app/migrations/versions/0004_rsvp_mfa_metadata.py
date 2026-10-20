"""Structured-only RSVP, admin MFA and server-recorded upload metadata."""

import sqlalchemy as sa
from alembic import op

revision = "0004_rsvp_mfa_metadata"
down_revision = "0003_media"
branch_labels = depends_on = None


def columns():
    return {
        "invitations": [
            sa.Column("has_rsvp", sa.Boolean(), nullable=False, server_default=sa.false())
        ],
        "admin_users": [
            sa.Column("totp_secret", sa.Text(), nullable=False, server_default=""),
            sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("totp_last_step", sa.Integer(), nullable=False, server_default="-1"),
        ],
        "photos": [
            *[
                sa.Column(
                    name,
                    sa.BigInteger() if name == "duration_ms" else sa.Integer(),
                    nullable=False,
                    server_default="0",
                )
                for name in ("uploaded_at", "completed_at", "width", "height", "duration_ms")
            ],
            *[
                sa.Column(name, sa.String(length), nullable=False, server_default="")
                for name, length in [
                    ("original_filename", 200),
                    ("uploader_name", 100),
                    ("codec", 40),
                    ("sha256", 64),
                ]
            ],
        ],
    }


def upgrade():
    for table, additions in columns().items():
        for column in additions:
            with op.get_context().autocommit_block():
                op.add_column(table, column)
    op.execute(
        "UPDATE invitations SET has_rsvp = true WHERE id IN (SELECT invitation_id FROM rsvp_responses)"
    )
    with op.get_context().autocommit_block():
        op.drop_column("invitations", "rsvp_json")


def downgrade():
    with op.get_context().autocommit_block():
        op.add_column("invitations", sa.Column("rsvp_json", sa.Text(), nullable=True))
    for table, additions in reversed(list(columns().items())):
        for column in reversed(additions):
            with op.get_context().autocommit_block():
                op.drop_column(table, column.name)
