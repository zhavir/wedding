"""Human-friendly invitation codes, without putting credentials in URLs or logs."""

import hashlib
import hmac
import secrets
import time

from fastapi import HTTPException, Request
from sqlalchemy import case, update
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.security import cipher, digest
from app.db.models import AuthThrottle, Invitation, InvitationAccess, InvitationLink

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_code() -> str:
    raw = "".join(secrets.choice(ALPHABET) for _ in range(10))
    return raw[:5] + "-" + raw[5:]


def code_hash(code: str) -> str:
    normalized = "".join(code.upper().split()).replace("-", "")
    return hmac.new(
        settings().invite_encryption_key.encode(), normalized.encode(), hashlib.sha256
    ).hexdigest()


async def ensure_access(db, invitation_id: str) -> InvitationAccess:
    invite = await db.get(Invitation, invitation_id)
    if invite and not invite.encrypted_token:
        token = secrets.token_urlsafe(32)
        claimed = await db.scalar(
            update(Invitation)
            .where(Invitation.id == invitation_id, Invitation.encrypted_token == "")
            .values(encrypted_token=cipher().encrypt(token.encode()).decode())
            .returning(Invitation.id)
        )
        if claimed:
            db.add(InvitationLink(token_hash=digest(token), invitation_id=invitation_id))
        await db.flush()
        await db.refresh(invite)
    access = await db.get(InvitationAccess, invitation_id)
    if access is None:
        code = new_code()
        access = InvitationAccess(
            invitation_id=invitation_id,
            code_hash=code_hash(code),
            encrypted_code=cipher().encrypt(code.encode()).decode(),
            recovery_at=0,
            pending_expires=0,
        )
        db.add(access)
        await db.flush()
    return access


async def throttle(db, request: Request, scope: str, limit: int, seconds: int):
    peer = request.client.host if request.client else "unknown"
    key = code_hash(scope + ":" + peer)
    window = int(time.time()) // seconds
    if await db.get(AuthThrottle, key) is None:
        db.add(AuthThrottle(id=key, window=window, attempts=0))
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
    count = await db.scalar(
        update(AuthThrottle)
        .where(AuthThrottle.id == key)
        .values(
            attempts=case((AuthThrottle.window == window, AuthThrottle.attempts + 1), else_=1),
            window=window,
        )
        .returning(AuthThrottle.attempts)
    )
    await db.commit()
    if count is None or count > limit:
        raise HTTPException(
            429,
            "Too many attempts. Please wait before trying again.",
            headers={"Retry-After": str(seconds)},
        )
