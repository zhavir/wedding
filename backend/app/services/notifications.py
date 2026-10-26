"""Durable delivery state; an email failure never rolls back a guest's RSVP."""

import asyncio
import html
import time
import uuid

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Invitation, RSVPNotification
from app.db.session import sessions
from app.schemas import RSVP
from app.services.email import deliver_email
from app.services.mail_transport import EmailRejected, EmailUncertain


def queue_notification(db: AsyncSession, invite: Invitation, body: RSVP) -> str | None:
    recipient = settings().rsvp_notification_email
    if not recipient:
        return None
    key = uuid.uuid7().hex
    answer = "YES / SÌ" if body.attending else "NO"
    # Dietary information stays in the protected admin interface, not notification emails.
    text = f"{invite.name} replied: {answer}\nGuests: {len(body.guests)}\nReview the response: {settings().site_url.rstrip('/')}/api/admin/\n"
    db.add(
        RSVPNotification(
            id=key,
            invitation_id=invite.id,
            recipient=str(recipient),
            subject="Wedding RSVP / Risposta al matrimonio",
            body=text,
            status="pending",
            created_at=int(time.time()),
        )
    )
    return key


async def send_notification(key: str) -> None:
    async with sessions()() as db:
        claimed = await db.scalar(
            update(RSVPNotification)
            .where(RSVPNotification.id == key, RSVPNotification.status == "pending")
            .values(status="sending")
            .returning(RSVPNotification.id)
        )
        await db.commit()
        if not claimed:
            return
        item = await db.get(RSVPNotification, key)
        assert item is not None
        try:
            await asyncio.to_thread(
                deliver_email,
                item.recipient,
                {
                    "subject": item.subject,
                    "text": item.body,
                    "html": f'<div style="font:18px Arial;max-width:600px;margin:auto;line-height:1.6">{html.escape(item.body).replace(chr(10), "<br>")}</div>',
                },
            )
            item.status = "sent"
        except EmailRejected as exc:
            item.status = "failed"
            item.error = str(exc)
        except EmailUncertain:
            item.status = "unknown"
            item.error = "Delivery uncertain. Check the email provider before resending."
        await db.commit()
