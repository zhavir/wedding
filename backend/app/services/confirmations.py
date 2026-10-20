"""Persist acceptance emails before delivery, including their calendar attachment."""

import asyncio
import time
import uuid
from email.message import EmailMessage
from email.policy import SMTP

from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import ConfirmationEmail, Invitation
from app.db.session import sessions
from app.schemas import RSVP
from app.services.aws import ses
from app.services.calendar import wedding_calendar
from app.services.email import content, templates


def queue_confirmation(db: AsyncSession, invite: Invitation, body: RSVP) -> str:
    wedding = content(invite.language or "en")
    copy = wedding["confirmationEmail"]
    intro = copy["witnessIntro"] if invite.is_witness else copy["intro"]
    key = uuid.uuid7().hex
    text = f"{invite.name},\n\n{intro}\n\n{wedding['dateLabel']}\n{wedding['venue']}\n{wedding['address']}\n\n{copy['calendarHelp']}\n{settings().site_url.rstrip('/')}/\n"
    db.add(
        ConfirmationEmail(
            id=key,
            invitation_id=invite.id,
            recipient=str(body.email),
            subject=copy["subject"],
            text_body=text,
            html_body=templates.get_template("confirmation.html").render(
                w=wedding,
                copy=copy,
                intro=intro,
                guest=invite,
                language=invite.language or "en",
                site_url=settings().site_url,
            ),
            calendar=wedding_calendar(wedding, settings().site_url),
            status="pending",
            created_at=int(time.time()),
        )
    )
    return key


def deliver_confirmation(item: ConfirmationEmail):
    message = EmailMessage(policy=SMTP)
    message["From"] = settings().email_from
    message["To"] = item.recipient
    message["Subject"] = item.subject
    message.set_content(item.text_body)
    message.add_alternative(item.html_body, subtype="html")
    message.add_attachment(
        item.calendar.encode("utf-8"),
        maintype="text",
        subtype="calendar",
        filename="andrea-sara-wedding.ics",
        params={"charset": "UTF-8", "method": "PUBLISH"},
    )
    return ses().send_raw_email(
        Source=settings().email_from,
        Destinations=[item.recipient],
        RawMessage={"Data": message.as_bytes()},
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
            result = await asyncio.to_thread(deliver_confirmation, item)
            item.status, item.message_id = "sent", result["MessageId"]
        except ClientError as exc:
            item.status = "failed"
            item.error = str(exc.response.get("Error", {}).get("Code", "Email rejected"))
        except BotoCoreError:
            item.status = "unknown"
            item.error = "Delivery uncertain. Check SES before resending."
        await db.commit()
