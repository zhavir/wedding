import hashlib
from typing import Annotated

from cryptography.fernet import Fernet
from fastapi import Cookie, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Invitation, Session
from app.db.session import get_db

DB = Annotated[AsyncSession, Depends(get_db)]
COOKIE_NAME = "wedding_session"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def cipher() -> Fernet:
    return Fernet(settings().invite_encryption_key.encode())


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings().session_days * 86400,
        httponly=True,
        secure=settings().cookie_secure,
        samesite="lax",
        path="/api",
    )


async def current_guest(
    db: DB, response: Response, wedding_session: Annotated[str | None, Cookie()] = None
) -> Invitation:
    if not wedding_session:
        raise HTTPException(401, "Please open the personal link in your invitation email.")
    session = await db.get(Session, digest(wedding_session))
    invite = await db.get(Invitation, session.invitation_id) if session and session.active else None
    if invite is None or not invite.active:
        raise HTTPException(401, "This invitation or session is no longer active.")
    set_session_cookie(response, wedding_session)
    return invite


Guest = Annotated[Invitation, Depends(current_guest)]


async def current_admin(guest: Guest) -> Invitation:
    # Legacy endpoints support local fixtures only. Production administration
    # must use SQLAdmin's independent password + authenticator session.
    if settings().cookie_secure or settings().dsql_host:
        raise HTTPException(403, "Use the administrator login with two-factor authentication.")
    if not guest.is_admin:
        raise HTTPException(403, "Administrator access is required.")
    return guest


Admin = Annotated[Invitation, Depends(current_admin)]
