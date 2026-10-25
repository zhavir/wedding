"""Persist acceptance emails before delivery, with a static calendar attachment."""

import asyncio
import time
import uuid
from email.message import EmailMessage
from email.policy import SMTP
from pathlib import Path

from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import ConfirmationEmail, Invitation
from app.db.session import sessions
from app.schemas import RSVP
from app.services.aws import ses
from app.services.email import content, templates
from app.services.email_content import participant_copy


async def render_confirmation(
    invite: Invitation, participant_count: int, db: AsyncSession | None = None
) -> dict[str, str]:
    wedding = await content(invite.guest.language or "en", db)
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
            language=invite.guest.language or "en",
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
    return (assets / f"wedding-{'it' if language == 'it' else 'en'}.ics").read_bytes()


def deliver_confirmation(item: ConfirmationEmail, language: str):
    message = EmailMessage(policy=SMTP)
    message["From"] = settings().email_from
    message["To"] = item.recipient
    message["Subject"] = item.subject
    message.set_content(item.text_body)
    message.add_alternative(item.html_body, subtype="html")
    message.add_attachment(
        calendar_attachment(language),
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
            invite = await db.get(Invitation, item.invitation_id)
            assert invite is not None
            result = await asyncio.to_thread(deliver_confirmation, item, invite.guest.language)
            item.status, item.message_id = "sent", result["MessageId"]
        except ClientError as exc:
            item.status = "failed"
            item.error = str(exc.response.get("Error", {}).get("Code", "Email rejected"))
        except BotoCoreError:
            item.status = "unknown"
            item.error = "Delivery uncertain. Check SES before resending."
        await db.commit()
