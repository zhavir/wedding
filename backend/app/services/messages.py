"""Validated plain-text templates, selected once per invitation and language."""

import secrets
from string import Formatter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Invitation, InvitationMessage, InvitationMessageChoice

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
    audience = "witness" if invite.is_witness else "guest"
    locale = invite.language or "en"
    saved = await db.get(InvitationMessageChoice, invite.id)
    if saved and saved.language == locale and saved.audience == audience:
        return saved.text
    pool = list(
        await db.scalars(
            select(InvitationMessage)
            .where(
                InvitationMessage.active.is_(True),
                InvitationMessage.language == locale,
                InvitationMessage.audience == audience,
            )
            .order_by(InvitationMessage.id)
        )
    )
    if not pool:
        return None  # Caller uses the matching locale's editable default, never another language.
    selected = secrets.choice(pool).text
    if saved is None:
        saved = InvitationMessageChoice(invitation_id=invite.id)
        db.add(saved)
    saved.language, saved.audience, saved.text = locale, audience, selected
    return selected


def render_message(template: str, invite: Invitation, wedding: dict) -> str:
    validate_message(template)
    return template.format(
        name=invite.name,
        couple=" & ".join(wedding["names"]),
        date=wedding["dateLabel"],
        venue=wedding["venue"],
    )
