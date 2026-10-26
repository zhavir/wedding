import asyncio
from copy import deepcopy

from jinja2 import Environment, PackageLoader, select_autoescape
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import cipher
from app.db.models import Guest, Invitation
from app.db.session import sessions
from app.services.access import ensure_access
from app.services.email_content import CONTENT, participant_copy
from app.services.invitations import invitation_link
from app.services.mail_transport import EmailRejected, EmailUncertain, send_message
from app.services.messages import invitation_message, render_message

templates = Environment(
    loader=PackageLoader("app", "templates"), autoescape=select_autoescape(["html"])
)


async def content(language: str = "it", db: AsyncSession | None = None) -> dict:
    wedding = deepcopy(CONTENT["en" if language == "en" else "it"])
    wedding["contactEmail"] = settings().email_from
    return wedding


def render_email(
    invite: Invitation,
    short_code: str = "",
    *,
    wedding: dict,
    link: str | None = None,
    message_template: str | None = None,
) -> dict[str, str]:
    wedding = participant_copy(wedding, invite.guest.language, invite.max_guests)
    if invite.is_witness:
        wedding = {**wedding, "email": wedding["witnessEmail"]}
    if message_template:
        wedding = {
            **wedding,
            "email": {
                **wedding["email"],
                "intro": render_message(message_template, invite, wedding),
            },
        }
    url = link or invitation_link(invite)
    return {
        "subject": wedding["email"]["subject"],
        "html": templates.get_template(
            f"invitation_{'en' if invite.guest.language == 'en' else 'it'}.html"
        ).render(
            w=wedding,
            guest=invite,
            link=url,
            short_code=short_code,
            language=invite.guest.language or "it",
            logo_url=f"{settings().site_url.rstrip('/')}/monogram.png",
        ),
        "text": f"{'Dear' if invite.guest.language == 'en' else 'Ciao'} {invite.name},\n\n{wedding['email']['intro']}\n\n{wedding['dateLabel']} · {wedding['venue']}\n\n{url}\n\nInvitation code / Codice invito: {short_code}\n\n{wedding['email']['footer']}",
    }


async def send_invitation(invitation_id: str) -> dict[str, str]:
    # Commit before delivery so concurrent requests cannot send the same draft twice.
    async with sessions()() as db:
        claimed = await db.scalar(
            update(Invitation)
            .where(
                Invitation.id == invitation_id,
                Invitation.active.is_(True),
                Invitation.guest.has(Guest.email != ""),
                Invitation.is_admin.is_(False),
                Invitation.email_status.in_(["draft", "failed"]),
            )
            .values(email_status="sending", email_error=None)
            .returning(Invitation.id)
        )
        await db.commit()
        if not claimed:
            return {"id": invitation_id, "status": "skipped"}
        invite = await db.get(Invitation, invitation_id)
        if invite is None or not invite.guest.email:
            return {"id": invitation_id, "status": "skipped"}
        access = await ensure_access(db, invite.id)
        selected_message = await invitation_message(db, invite)
        await db.commit()
        message = render_email(
            invite,
            cipher().decrypt(access.encrypted_code.encode()).decode(),
            message_template=selected_message,
            wedding=await content(invite.guest.language or "it", db),
        )
        try:
            result = await asyncio.to_thread(deliver_email, invite.guest.email, message)
            invite.email_message_id = result["MessageId"]
            invite.email_status = "sent"
        except EmailRejected as exc:
            invite.email_status = "failed"
            invite.email_error = str(exc)
        except EmailUncertain:
            invite.email_status = "unknown"
            invite.email_error = "Delivery uncertain. Check the email provider before resending."
        await db.commit()
        return {
            "id": invitation_id,
            "status": invite.email_status,
            "error": invite.email_error or "",
        }


def deliver_email(email: str, message: dict[str, str]):
    return send_message(email, message)
