"""Password and TOTP authentication, independent of guest invitation links."""

import asyncio
import hashlib
import hmac
import secrets
import time

from sqladmin.authentication import AuthenticationBackend
from sqlalchemy import update
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.db.models import AdminUser
from app.db.session import sessions
from app.services.totp import consume_code, new_secret


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    key = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
    return f"scrypt${salt}${key.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        _, salt, _ = encoded.split("$")
        return hmac.compare_digest(hash_password(password, salt), encoded)
    except ValueError, TypeError:
        return False


async def failed_attempt(db, user: AdminUser) -> None:
    count = await db.scalar(
        update(AdminUser)
        .where(AdminUser.username == user.username)
        .values(failed_attempts=AdminUser.failed_attempts + 1)
        .returning(AdminUser.failed_attempts)
    )
    if count and count >= 5:
        user.locked_until = int(time.time()) + 900
        user.failed_attempts = 0
    await db.commit()


def authenticated_session(request: Request, user: AdminUser) -> None:
    request.session.clear()
    request.session.update(user_id=user.username, version=user.version, mfa_authenticated=True)


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request):
        form = await request.form()
        username = str(form.get("username", "")).strip().lower()
        password = str(form.get("password", ""))
        code = str(form.get("otp", "")).strip()
        if len(username) > 100 or len(password) > 1024:
            return False
        async with sessions()() as db:
            user = await db.get(AdminUser, username)
            encoded = user.password_hash if user else "scrypt$" + "00" * 16 + "$" + "00" * 64
            valid = await asyncio.to_thread(verify_password, password, encoded)
            if not user or not user.active or user.locked_until > int(time.time()):
                return False
            if not valid:
                await failed_attempt(db, user)
                return False
            if not user.totp_enabled:
                if not user.totp_secret:
                    user.totp_secret = new_secret()
                await db.commit()
                request.session.clear()
                request.session.update(
                    mfa_user=user.username,
                    version=user.version,
                    mfa_expires=int(time.time()) + 300,
                    mfa_csrf=secrets.token_urlsafe(32),
                )
                return RedirectResponse(request.url_for("admin:view-mfa"), status_code=303)
            if not await consume_code(db, user, code):
                await failed_attempt(db, user)
                return False
            user.failed_attempts = user.locked_until = 0
            await db.commit()
            authenticated_session(request, user)
            return True

    async def authenticate(self, request: Request) -> bool:
        pending = request.url.path.rstrip("/") == "/api/admin/mfa"
        username = request.session.get("mfa_user" if pending else "user_id")
        if not isinstance(username, str):
            return False
        if pending and request.session.get("mfa_expires", 0) < time.time():
            return False
        async with sessions()() as db:
            user = await db.get(AdminUser, username)
            if not user or not user.active or user.version != request.session.get("version"):
                return False
            return bool(pending or (user.totp_enabled and request.session.get("mfa_authenticated")))

    async def logout(self, request: Request) -> bool:
        username = request.session.get("user_id")
        if isinstance(username, str):
            async with sessions()() as db:
                user = await db.get(AdminUser, username)
                if user:
                    user.version = secrets.token_hex(24)
                    await db.commit()
        request.session.clear()
        return True
