"""Ephemeral, random browser-test credentials, only for the local Docker stack."""

import asyncio
import json
import secrets
import socket
from pathlib import Path

import pyotp
from app.admin.auth import hash_password
from app.core.config import settings
from app.core.security import cipher, digest
from app.db.models import AdminUser, AuthThrottle, Invitation, InvitationLink
from app.db.session import engine, sessions
from app.services.access import code_hash
from sqlalchemy import delete


async def main():
    if settings().dsql_host or settings().cookie_secure:
        raise RuntimeError("Browser test accounts may only be created locally")
    if settings().aws_endpoint_url != "http://floci:4566":
        raise RuntimeError("Browser fixtures require the isolated Compose Floci endpoint")
    # The frontend proxy is the API peer for browser requests. Reset only its
    # local test counters, not arbitrary guests or production rate limits.
    peers = {item[4][0] for item in socket.getaddrinfo("web", 5173)}
    keys = [code_hash(f"{scope}:{peer}") for scope in ("login", "recovery") for peer in peers]
    password = secrets.token_urlsafe(32)
    async with sessions()() as db:
        await db.execute(delete(AuthThrottle).where(AuthThrottle.id.in_(keys)))
        link = await db.get(InvitationLink, digest("DEMO-LOVE-2027"))
        if link:
            guest = await db.get(Invitation, link.invitation_id)
            if guest:
                guest.uploads = 0
        accounts = []
        password_hash = await asyncio.to_thread(hash_password, password)
        for index in range(64):
            username = f"browser-test-admin-{index}"
            user = await db.get(AdminUser, username)
            if user is None:
                user = AdminUser(username=username)
                db.add(user)
            secret = pyotp.random_base32()
            user.password_hash = password_hash
            user.version = secrets.token_hex(24)
            user.active = True
            user.failed_attempts = user.locked_until = 0
            user.totp_secret = cipher().encrypt(secret.encode()).decode()
            user.totp_enabled = True
            user.totp_last_step = -1
            accounts.append({"username": username, "password": password, "secret": secret})
        await db.commit()
    Path("/credentials/admin.json").write_text(json.dumps({"accounts": accounts}))
    await engine().dispose()


asyncio.run(main())
