import asyncio
import secrets
import time
from contextlib import suppress

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import func, or_, select, update

from app.core.config import settings
from app.core.security import COOKIE_NAME, DB, Guest, cipher, digest, set_session_cookie
from app.db.models import Invitation, InvitationAccess, InvitationLink, Session
from app.schemas import Login, RecoverInvitation
from app.services.access import code_hash, ensure_access, new_code, throttle
from app.services.email import content, deliver_email, render_email

router = APIRouter()


def guest_view(invite: Invitation) -> dict[str, object]:
    return {
        "id": invite.id,
        "name": invite.name,
        "max_guests": invite.max_guests,
        "is_admin": invite.is_admin,
        "is_witness": bool(invite.is_witness),
    }


@router.post("/session")
async def login(body: Login, db: DB, response: Response, request: Request):
    await throttle(db, request, "login", 60, 60)
    submitted = body.code.strip()
    link = await db.get(InvitationLink, digest(submitted))
    invite = await db.get(Invitation, link.invitation_id) if link else None
    if invite and not secrets.compare_digest(
        cipher().decrypt(invite.encrypted_token.encode()).decode(), submitted
    ):
        invite = None  # A replaced long link cannot be reused.
    if invite is None:
        access = await db.scalar(
            select(InvitationAccess).where(
                or_(
                    InvitationAccess.code_hash == code_hash(submitted),
                    InvitationAccess.pending_code_hash == code_hash(submitted),
                    InvitationAccess.pending_link_hash == digest(submitted),
                )
            )
        )
        invite = await db.get(Invitation, access.invitation_id) if access else None
        if access and invite and access.code_hash != code_hash(submitted):
            if (
                access.pending_expires <= int(time.time())
                or not access.pending_code
                or not access.pending_link
            ):
                invite = None
            elif invite.active:
                # Promote replacements only after the recipient uses the delivered code/link.
                access.code_hash = code_hash(
                    cipher().decrypt(access.pending_code.encode()).decode()
                )
                access.encrypted_code = access.pending_code
                invite.encrypted_token = access.pending_link
                token = cipher().decrypt(access.pending_link.encode()).decode()
                db.add(InvitationLink(token_hash=digest(token), invitation_id=invite.id))
                access.pending_code_hash = access.pending_code = None
                access.pending_link_hash = access.pending_link = None
                access.pending_expires = 0
    if invite is None or not invite.active:
        raise HTTPException(401, "We couldn't find that invitation. Please check your code.")
    token = secrets.token_urlsafe(48)
    db.add(Session(token_hash=digest(token), invitation_id=invite.id, active=True))
    await db.commit()
    set_session_cookie(response, token)
    return guest_view(invite)


@router.post("/session/recover", status_code=202)
async def recover(body: RecoverInvitation, db: DB, request: Request):
    await throttle(db, request, "recovery", 5, 900)
    # Never reveal whether this address belongs to a guest. No new guest records are created.
    invites = list(
        await db.scalars(
            select(Invitation)
            .where(
                func.lower(Invitation.email) == str(body.email).lower(),
                Invitation.active.is_(True),
                Invitation.is_admin.is_(False),
            )
            .limit(10)
        )
    )
    for invite in invites:
        if not invite.email:
            continue
        await ensure_access(db, invite.id)
        now = int(time.time())
        code, token = new_code(), secrets.token_urlsafe(32)
        claimed = await db.scalar(
            update(InvitationAccess)
            .where(
                InvitationAccess.invitation_id == invite.id,
                InvitationAccess.recovery_at <= now - 300,
            )
            .values(
                recovery_at=now,
                pending_code_hash=code_hash(code),
                pending_code=cipher().encrypt(code.encode()).decode(),
                pending_link_hash=digest(token),
                pending_link=cipher().encrypt(token.encode()).decode(),
                pending_expires=now + 900,
            )
            .returning(InvitationAccess.invitation_id)
        )
        await db.commit()
        if not claimed:
            continue
        message = render_email(
            invite,
            code,
            link=f"{settings().site_url.rstrip('/')}/#invite={token}",
            wedding=await content(invite.language or "en", db),
        )
        message["subject"] = "Your replacement invitation / Il tuo nuovo invito"
        message["text"] += (
            "\nUse this replacement within 15 minutes. / Usa il nuovo codice entro 15 minuti."
        )
        message["html"] = message["html"].replace(
            "</body>",
            '<p style="text-align:center">Use within 15 minutes / Da usare entro 15 minuti</p></body>',
        )
        # Failure does not invalidate the working invitation or disclose membership.
        with suppress(ClientError, BotoCoreError):
            await asyncio.to_thread(deliver_email, invite.email, message)
    return {
        "message": "If this email belongs to an active invitation, a replacement code and link will arrive shortly. Please check your spam folder."
    }


@router.get("/session")
async def me(invite: Guest):
    return guest_view(invite)


@router.delete("/session")
async def logout(request: Request, response: Response, db: DB):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        session = await db.get(Session, digest(token))
        if session:
            session.active = False
            await db.commit()
    response.delete_cookie(COOKIE_NAME, path="/api")
    return {"signed_out": True}
