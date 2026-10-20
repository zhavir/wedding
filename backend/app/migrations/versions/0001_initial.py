"""Initial Aurora DSQL schema and seed records (squashed revisions 0001-0007)."""

import os
import time

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


DEFAULTS = {
    ("en", "guest"): [
        "Dear {name}, our next chapter begins with the people we love. Join {couple} on {date} at {venue} for a day to remember.",
        "{name}, a celebration is only complete when our favourite people are there. We would love to see you at {venue} on {date}.",
        "Save a little space for love, laughter and dancing, {name}! Celebrate with {couple} at {venue} on {date}.",
    ],
    ("it", "guest"): [
        "{name}, il nostro nuovo capitolo inizia con le persone del cuore. Festeggia con {couple} il {date} a {venue}.",
        "Una festa è completa solo con le persone che amiamo, {name}. Ti aspettiamo il {date} a {venue} per una giornata da ricordare.",
        "{name}, tieni un posto per l’amore, i sorrisi e i balli! Festeggia insieme a {couple} il {date} a {venue}.",
    ],
    ("en", "witness"): [
        "{name}, will you stand beside {couple} as our witness on {date}? We would love to share this special moment with you at {venue}.",
        "Some people make every chapter more meaningful. {name}, we would be honoured to have you as our witness at {venue} on {date}.",
    ],
    ("it", "witness"): [
        "{name}, vuoi essere al fianco di {couple} come testimone il {date}? Ci piacerebbe condividere questo momento speciale con te a {venue}.",
        "Ci sono persone che rendono ogni capitolo più speciale. {name}, sarebbe un onore averti come testimone a {venue} il {date}.",
    ],
}


def upgrade():
    # Fail before schema changes if an operator bypassed release validation.
    if os.environ.get("DSQL_HOST"):
        for key in (
            "WEDDING_GROOM_NAME",
            "WEDDING_GROOM_EMAIL",
            "WEDDING_BRIDE_NAME",
            "WEDDING_BRIDE_EMAIL",
        ):
            if not os.environ.get(key, "").strip():
                raise ValueError(f"{key} is required for the initial production migration")
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
            sa.Column("email_status", sa.String(20), nullable=False, primary_key=False),
            sa.Column("email_message_id", sa.String(200), nullable=True, primary_key=False),
            sa.Column("email_error", sa.Text, nullable=True, primary_key=False),
            sa.Column("created_at", sa.Integer, nullable=False, primary_key=False),
            sa.Column("has_rsvp", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("parent_invitation_id", sa.String(64), nullable=False, server_default=""),
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
            sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("motion_size", sa.BigInteger(), nullable=False, server_default="0"),
            sa.Column("motion_content_type", sa.String(50), nullable=False, server_default=""),
            sa.Column("uploaded_at", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("completed_at", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("width", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("height", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("duration_ms", sa.BigInteger(), nullable=False, server_default="0"),
            sa.Column("original_filename", sa.String(200), nullable=False, server_default=""),
            sa.Column("uploader_name", sa.String(100), nullable=False, server_default=""),
            sa.Column("codec", sa.String(40), nullable=False, server_default=""),
            sa.Column("sha256", sa.String(64), nullable=False, server_default=""),
            sa.Column("storage_prefix", sa.String(65), nullable=False, server_default=""),
            sa.Column("multipart_id", sa.Text(), nullable=False, server_default=""),
            sa.Column("motion_multipart_id", sa.Text(), nullable=False, server_default=""),
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
            sa.Column("totp_secret", sa.Text(), nullable=False, server_default=""),
            sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("totp_last_step", sa.Integer(), nullable=False, server_default="-1"),
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
            sa.Column("email", sa.String(254), nullable=False, server_default=""),
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

    # Seed the invitation text templates and initial wedding host invitations.
    with op.get_context().autocommit_block():
        op.create_table(
            "invitation_messages",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("language", sa.String(2), nullable=False),
            sa.Column("audience", sa.String(10), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False),
            if_not_exists=True,
        )
    with op.get_context().autocommit_block():
        op.create_table(
            "invitation_message_choices",
            sa.Column("invitation_id", sa.String(64), primary_key=True),
            sa.Column("language", sa.String(2), nullable=False),
            sa.Column("audience", sa.String(10), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            if_not_exists=True,
        )
    table = sa.table(
        "invitation_messages",
        sa.column("id", sa.String),
        sa.column("language", sa.String),
        sa.column("audience", sa.String),
        sa.column("text", sa.Text),
        sa.column("active", sa.Boolean),
    )
    op.bulk_insert(
        table,
        [
            {
                "id": f"default-{locale}-{audience}-{index}",
                "language": locale,
                "audience": audience,
                "text": message,
                "active": True,
            }
            for (locale, audience), messages in DEFAULTS.items()
            for index, message in enumerate(messages)
        ],
    )

    for identity, name, email in [
        (
            "wedding-groom",
            os.environ.get("WEDDING_GROOM_NAME", "Wedding groom"),
            os.environ.get("WEDDING_GROOM_EMAIL", "groom@example.com"),
        ),
        (
            "wedding-bride",
            os.environ.get("WEDDING_BRIDE_NAME", "Wedding bride"),
            os.environ.get("WEDDING_BRIDE_EMAIL", "bride@example.com"),
        ),
    ]:
        op.get_bind().execute(
            sa.text("""
            INSERT INTO invitations
            (id, name, email, language, max_guests, active, is_admin, is_witness,
             encrypted_token, uploads, has_rsvp, email_status, created_at, parent_invitation_id)
            VALUES (:id, :name, :email, 'it', 1, true, false, false, '', 0, false, 'draft', :created_at, '')
        """),
            dict(id=identity, name=name, email=email, created_at=int(time.time())),
        )


def downgrade():
    with op.get_context().autocommit_block():
        op.drop_table("invitation_message_choices")
    with op.get_context().autocommit_block():
        op.drop_table("invitation_messages")
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
