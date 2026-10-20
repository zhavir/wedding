"""Initial SQL schema, frozen before the first release."""

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    with op.get_context().autocommit_block():
        op.create_table(
            "invitations",
            sa.Column("id", sa.String(64), nullable=False, primary_key=True),
            sa.Column("name", sa.String(100), nullable=False, primary_key=False),
            sa.Column("email", sa.String(254), nullable=False, primary_key=False),
            sa.Column(
                "language", sa.String(2), nullable=False, primary_key=False, server_default="en"
            ),
            sa.Column("max_guests", sa.Integer, nullable=False, primary_key=False),
            sa.Column("active", sa.Boolean, nullable=False, primary_key=False),
            sa.Column("is_admin", sa.Boolean, nullable=False, primary_key=False),
            sa.Column(
                "is_witness", sa.Boolean, nullable=False, primary_key=False, server_default="false"
            ),
            sa.Column("encrypted_token", sa.Text, nullable=False, primary_key=False),
            sa.Column("uploads", sa.Integer, nullable=False, primary_key=False),
            sa.Column("rsvp_json", sa.Text, nullable=True, primary_key=False),
            sa.Column("email_status", sa.String(20), nullable=False, primary_key=False),
            sa.Column("email_message_id", sa.String(200), nullable=True, primary_key=False),
            sa.Column("email_error", sa.Text, nullable=True, primary_key=False),
            sa.Column("created_at", sa.Integer, nullable=False, primary_key=False),
            if_not_exists=True,
        )
    with op.get_context().autocommit_block():
        op.create_table(
            "invitation_links",
            sa.Column("token_hash", sa.String(64), nullable=False, primary_key=True),
            sa.Column("invitation_id", sa.String(64), nullable=False, primary_key=False),
            if_not_exists=True,
        )
    with op.get_context().autocommit_block():
        op.create_table(
            "sessions",
            sa.Column("token_hash", sa.String(64), nullable=False, primary_key=True),
            sa.Column("invitation_id", sa.String(64), nullable=False, primary_key=False),
            sa.Column("active", sa.Boolean, nullable=False, primary_key=False),
            if_not_exists=True,
        )
    with op.get_context().autocommit_block():
        op.create_table(
            "photos",
            sa.Column("id", sa.String(64), nullable=False, primary_key=True),
            sa.Column("owner", sa.String(64), nullable=False, primary_key=False),
            sa.Column("size", sa.BigInteger, nullable=False, primary_key=False),
            sa.Column("content_type", sa.String(50), nullable=False, primary_key=False),
            sa.Column("caption", sa.String(200), nullable=False, primary_key=False),
            sa.Column("status", sa.String(20), nullable=False, primary_key=False),
            sa.Column("expires", sa.Integer, nullable=False, primary_key=False),
            if_not_exists=True,
        )
    with op.get_context().autocommit_block():
        op.create_table(
            "admin_users",
            sa.Column("username", sa.String(100), nullable=False, primary_key=True),
            sa.Column("password_hash", sa.Text, nullable=False, primary_key=False),
            sa.Column("version", sa.String(64), nullable=False, primary_key=False),
            sa.Column("active", sa.Boolean, nullable=False, primary_key=False),
            sa.Column("failed_attempts", sa.Integer, nullable=False, primary_key=False),
            sa.Column("locked_until", sa.Integer, nullable=False, primary_key=False),
            if_not_exists=True,
        )
    with op.get_context().autocommit_block():
        op.create_table(
            "invitation_access",
            sa.Column("invitation_id", sa.String(64), nullable=False, primary_key=True),
            sa.Column("code_hash", sa.String(64), nullable=False, primary_key=False),
            sa.Column("encrypted_code", sa.Text, nullable=False, primary_key=False),
            sa.Column("recovery_at", sa.Integer, nullable=False, primary_key=False),
            sa.Column("pending_code_hash", sa.String(64), nullable=True, primary_key=False),
            sa.Column("pending_code", sa.Text, nullable=True, primary_key=False),
            sa.Column("pending_link_hash", sa.String(64), nullable=True, primary_key=False),
            sa.Column("pending_link", sa.Text, nullable=True, primary_key=False),
            sa.Column("pending_expires", sa.Integer, nullable=False, primary_key=False),
            if_not_exists=True,
        )
    with op.get_context().autocommit_block():
        op.create_table(
            "auth_throttle",
            sa.Column("id", sa.String(64), nullable=False, primary_key=True),
            sa.Column("window", sa.Integer, nullable=False, primary_key=False),
            sa.Column("attempts", sa.Integer, nullable=False, primary_key=False),
            if_not_exists=True,
        )
    with op.get_context().autocommit_block():
        op.create_table(
            "rsvp_responses",
            sa.Column("invitation_id", sa.String(64), nullable=False, primary_key=True),
            sa.Column("email", sa.String(254), nullable=False, primary_key=False),
            sa.Column("attending", sa.Boolean, nullable=False, primary_key=False),
            sa.Column("message", sa.Text, nullable=False, primary_key=False),
            sa.Column("consent", sa.Boolean, nullable=False, primary_key=False),
            sa.Column("updated_at", sa.Integer, nullable=False, primary_key=False),
            if_not_exists=True,
        )
    with op.get_context().autocommit_block():
        op.create_table(
            "rsvp_guests",
            sa.Column("id", sa.String(80), nullable=False, primary_key=True),
            sa.Column("invitation_id", sa.String(64), nullable=False, primary_key=False),
            sa.Column("position", sa.Integer, nullable=False, primary_key=False),
            sa.Column("name", sa.String(100), nullable=False, primary_key=False),
            sa.Column("dietary", sa.Text, nullable=False, primary_key=False),
            sa.Column("active", sa.Boolean, nullable=False, primary_key=False),
            if_not_exists=True,
        )
    with op.get_context().autocommit_block():
        op.create_table(
            "rsvp_notifications",
            sa.Column("id", sa.String(64), nullable=False, primary_key=True),
            sa.Column("invitation_id", sa.String(64), nullable=False, primary_key=False),
            sa.Column("recipient", sa.String(254), nullable=False, primary_key=False),
            sa.Column("subject", sa.String(200), nullable=False, primary_key=False),
            sa.Column("body", sa.Text, nullable=False, primary_key=False),
            sa.Column("status", sa.String(20), nullable=False, primary_key=False),
            sa.Column("error", sa.Text, nullable=True, primary_key=False),
            sa.Column("created_at", sa.Integer, nullable=False, primary_key=False),
            if_not_exists=True,
        )
    with op.get_context().autocommit_block():
        op.create_table(
            "witness_responses",
            sa.Column("invitation_id", sa.String(64), nullable=False, primary_key=True),
            sa.Column("accepted", sa.Boolean, nullable=False, primary_key=False),
            if_not_exists=True,
        )
    with op.get_context().autocommit_block():
        op.create_table(
            "confirmation_emails",
            sa.Column("id", sa.String(64), nullable=False, primary_key=True),
            sa.Column("invitation_id", sa.String(64), nullable=False, primary_key=False),
            sa.Column("recipient", sa.String(254), nullable=False, primary_key=False),
            sa.Column("subject", sa.String(200), nullable=False, primary_key=False),
            sa.Column("text_body", sa.Text, nullable=False, primary_key=False),
            sa.Column("html_body", sa.Text, nullable=False, primary_key=False),
            sa.Column("calendar", sa.Text, nullable=False, primary_key=False),
            sa.Column("status", sa.String(20), nullable=False, primary_key=False),
            sa.Column("error", sa.Text, nullable=True, primary_key=False),
            sa.Column("message_id", sa.String(200), nullable=True, primary_key=False),
            sa.Column("created_at", sa.Integer, nullable=False, primary_key=False),
            if_not_exists=True,
        )


def downgrade():
    with op.get_context().autocommit_block():
        op.drop_table("confirmation_emails")
    with op.get_context().autocommit_block():
        op.drop_table("witness_responses")
    with op.get_context().autocommit_block():
        op.drop_table("rsvp_notifications")
    with op.get_context().autocommit_block():
        op.drop_table("rsvp_guests")
    with op.get_context().autocommit_block():
        op.drop_table("rsvp_responses")
    with op.get_context().autocommit_block():
        op.drop_table("auth_throttle")
    with op.get_context().autocommit_block():
        op.drop_table("invitation_access")
    with op.get_context().autocommit_block():
        op.drop_table("admin_users")
    with op.get_context().autocommit_block():
        op.drop_table("photos")
    with op.get_context().autocommit_block():
        op.drop_table("sessions")
    with op.get_context().autocommit_block():
        op.drop_table("invitation_links")
    with op.get_context().autocommit_block():
        op.drop_table("invitations")
