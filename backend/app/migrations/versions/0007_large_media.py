"""Multipart upload tracking and 64-bit media sizes/durations."""

import sqlalchemy as sa
from alembic import op

revision = "0007_large_media"
down_revision = "0006_wedding_hosts"
branch_labels = depends_on = None


def upgrade():
    for name in ["multipart_id", "motion_multipart_id"]:
        with op.get_context().autocommit_block():
            op.add_column("photos", sa.Column(name, sa.Text(), nullable=False, server_default=""))
    # Fresh schemas already use bigint; upgrade existing local pre-release data too.
    types = {
        column["name"]: column["type"] for column in sa.inspect(op.get_bind()).get_columns("photos")
    }
    for name in ["size", "motion_size", "duration_ms"]:
        if not isinstance(types[name], sa.BigInteger):
            if op.get_bind().dialect.name == "sqlite":
                with op.batch_alter_table("photos") as batch:
                    batch.alter_column(name, existing_type=sa.Integer(), type_=sa.BigInteger())
            else:
                with op.get_context().autocommit_block():
                    op.alter_column(
                        "photos", name, existing_type=sa.Integer(), type_=sa.BigInteger()
                    )


def downgrade():
    for name in ["motion_multipart_id", "multipart_id"]:
        with op.get_context().autocommit_block():
            op.drop_column("photos", name)
