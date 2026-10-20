"""Create bride and groom guest records; credentials are provisioned on first use."""

import time

import sqlalchemy as sa
from alembic import op

revision = "0006_wedding_hosts"
down_revision = "0005_additional_guests"
branch_labels = depends_on = None


def upgrade():
    for identity, name, email in [
        ("wedding-groom", "Andrea Aramini", "andrea.aramini.lavoro@gmail.com"),
        ("wedding-bride", "Sara Donciglio", "donciglio.sa@gmail.com"),
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
    for table, column in [
        ("sessions", "invitation_id"),
        ("invitation_links", "invitation_id"),
        ("invitation_access", "invitation_id"),
        ("invitations", "id"),
    ]:
        op.execute(
            sa.text(f"DELETE FROM {table} WHERE {column} IN ('wedding-groom', 'wedding-bride')")
        )
