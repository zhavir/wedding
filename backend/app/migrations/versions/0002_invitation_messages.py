"""Editable bilingual invitation messages and stable per-invitation selections."""

import sqlalchemy as sa
from alembic import op

revision = "0002_messages"
down_revision = "0001_initial"
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


def downgrade():
    with op.get_context().autocommit_block():
        op.drop_table("invitation_message_choices")
    with op.get_context().autocommit_block():
        op.drop_table("invitation_messages")
