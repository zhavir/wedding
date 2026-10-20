"""Private moderation queue and paired Live Photo metadata."""

import sqlalchemy as sa
from alembic import op

revision = "0003_media"
down_revision = "0002_messages"
branch_labels = depends_on = None


def upgrade():
    for column in [
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("motion_size", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("motion_content_type", sa.String(50), nullable=False, server_default=""),
    ]:
        with op.get_context().autocommit_block():
            op.add_column("photos", column)


def downgrade():
    for name in ["motion_content_type", "motion_size", "published"]:
        with op.get_context().autocommit_block():
            op.drop_column("photos", name)
