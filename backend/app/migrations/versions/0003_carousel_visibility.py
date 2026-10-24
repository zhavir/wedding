"""Separate authenticated carousel visibility from gallery moderation."""

import sqlalchemy as sa
from alembic import op

revision = "0003_carousel_visibility"
down_revision = "0002_email_copy"
branch_labels = None
depends_on = None


def upgrade():
    with op.get_context().autocommit_block():
        op.add_column("photos", sa.Column("carousel_visible", sa.Boolean(), nullable=True))
    op.execute(sa.text("UPDATE photos SET carousel_visible = false"))
    if op.get_bind().dialect.name != "sqlite":
        with op.get_context().autocommit_block():
            op.alter_column("photos", "carousel_visible", server_default=sa.false())


def downgrade():
    op.drop_column("photos", "carousel_visible")
