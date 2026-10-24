"""Validated plain-text invitation copy selected by language and guest audience."""

from string import Formatter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Invitation, InvitationMessage

FIELDS = {"name", "couple", "date", "venue"}


def validate_message(text: str) -> str:
    if not 1 <= len(text.strip()) <= 2000:
        raise ValueError("Use between 1 and 2000 characters.")
    for _, field, spec, conversion in Formatter().parse(text):
        if field is not None and (field not in FIELDS or spec or conversion):
            raise ValueError(
                "Allowed placeholders: {name}, {couple}, {date}, {venue}. Formatting and attribute access are not supported."
            )
    return text.strip()


async def invitation_message(db: AsyncSession, invite: Invitation) -> str | None:
    audience = (
        invite.guest.audience if invite.guest else ("witness" if invite.is_witness else "guest")
    )
    pool = list(
        await db.scalars(
            select(InvitationMessage)
            .where(
                InvitationMessage.active.is_(True),
                InvitationMessage.language == (invite.language or "en"),
                InvitationMessage.audience == audience,
            )
            .order_by(InvitationMessage.id)
        )
    )
    return pool[0].text if pool else None


def render_message(template: str, invite: Invitation, wedding: dict) -> str:
    validate_message(template)
    return template.format(
        name=invite.name,
        couple=" & ".join(wedding["names"]),
        date=wedding["dateLabel"],
        venue=wedding["venue"],
    )
