"""Linked additional invitations, guest emails and uploader storage prefixes."""

import sqlalchemy as sa
from alembic import op

revision = "0005_additional_guests"
down_revision = "0004_rsvp_mfa_metadata"
branch_labels = depends_on = None

FIELDS = [
    ("invitations", "parent_invitation_id", 64),
    ("rsvp_guests", "email", 254),
    ("photos", "storage_prefix", 65),
]


def upgrade():
    for table, name, length in FIELDS:
        with op.get_context().autocommit_block():
            op.add_column(
                table, sa.Column(name, sa.String(length), nullable=False, server_default="")
            )


def downgrade():
    for table, name, _ in reversed(FIELDS):
        with op.get_context().autocommit_block():
            op.drop_column(table, name)
