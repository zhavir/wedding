"""Persist acceptance emails before delivery, with a static calendar attachment."""

import asyncio
import time
import uuid
from pathlib import Path

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import ConfirmationEmail, Invitation
from app.db.session import sessions
from app.schemas import RSVP
from app.services.email import content, templates
from app.services.email_content import participant_copy
from app.services.mail_transport import EmailRejected, EmailUncertain, send_message


async def render_confirmation(
    invite: Invitation, participant_count: int, db: AsyncSession | None = None
) -> dict[str, str]:
    wedding = await content(invite.guest.language or "it", db)
    wedding = participant_copy(wedding, invite.guest.language, participant_count)
    copy = wedding["confirmationEmail"]
    intro = copy["intro"]
    text = f"{invite.name},\n\n{intro}\n\n{wedding['dateLabel']}\n{wedding['venue']}\n{wedding['address']}\n\n{copy['calendarHelp']}\n{settings().site_url.rstrip('/')}/\n"
    return {
        "subject": copy["subject"],
        "text": text,
        "html": templates.get_template("confirmation.html").render(
            w=wedding,
            copy=copy,
            intro=intro,
            guest=invite,
            language=invite.guest.language or "it",
            site_url=settings().site_url,
            logo_url=f"{settings().site_url.rstrip('/')}/monogram.png",
        ),
    }


async def queue_confirmation(db: AsyncSession, invite: Invitation, body: RSVP) -> str:
    message = await render_confirmation(invite, len(body.guests), db)
    key = uuid.uuid7().hex
    db.add(
        ConfirmationEmail(
            id=key,
            invitation_id=invite.id,
            recipient=str(body.email),
            subject=message["subject"],
            text_body=message["text"],
            html_body=message["html"],
            status="pending",
            created_at=int(time.time()),
        )
    )
    return key


def calendar_attachment(language: str) -> bytes:
    # Production packages receive these frontend-owned files during the image build.
    assets = Path(__file__).resolve().parents[1] / "assets"
    if not assets.is_dir():
        assets = Path(__file__).resolve().parents[3] / "frontend" / "static" / "calendar"
    return (assets / f"wedding-{'en' if language == 'en' else 'it'}.ics").read_bytes()


def deliver_confirmation(item: ConfirmationEmail, language: str):
    return send_message(
        item.recipient,
        {"subject": item.subject, "text": item.text_body, "html": item.html_body},
        attachment=calendar_attachment(language),
    )


async def send_confirmation(key: str) -> None:
    async with sessions()() as db:
        claimed = await db.scalar(
            update(ConfirmationEmail)
            .where(ConfirmationEmail.id == key, ConfirmationEmail.status == "pending")
            .values(status="sending")
            .returning(ConfirmationEmail.id)
        )
        await db.commit()
        if not claimed:
            return
        item = await db.get(ConfirmationEmail, key)
        assert item is not None
        try:
            invite = await db.get(Invitation, item.invitation_id)
            assert invite is not None
            result = await asyncio.to_thread(deliver_confirmation, item, invite.guest.language)
            item.status, item.message_id = "sent", result["MessageId"]
        except EmailRejected as exc:
            item.status = "failed"
            item.error = str(exc)
        except EmailUncertain:
            item.status = "unknown"
            item.error = "Delivery uncertain. Check the email provider before resending."
        await db.commit()
