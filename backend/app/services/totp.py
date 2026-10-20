"""Authenticator-app TOTP with encrypted secrets and atomic replay protection."""

import time
from datetime import UTC, datetime

import pyotp
from sqlalchemy import update

from app.core.security import cipher
from app.db.models import AdminUser


def new_secret() -> str:
    return cipher().encrypt(pyotp.random_base32().encode()).decode()


def authenticator(user: AdminUser) -> pyotp.TOTP:
    return pyotp.TOTP(cipher().decrypt(user.totp_secret.encode()).decode())


async def consume_code(db, user: AdminUser, code: str) -> bool:
    if len(code) != 6 or not code.isascii() or not code.isdigit() or not user.totp_secret:
        return False
    totp = authenticator(user)
    current = int(time.time()) // totp.interval
    for step in (current, current - 1, current + 1):
        if step <= user.totp_last_step or not totp.verify(
            code, for_time=datetime.fromtimestamp(step * totp.interval, UTC)
        ):
            continue
        claimed = await db.scalar(
            update(AdminUser)
            .where(AdminUser.username == user.username, AdminUser.totp_last_step < step)
            .values(totp_last_step=step)
            .returning(AdminUser.username)
        )
        return claimed is not None
    return False
