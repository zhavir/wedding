"""Operator commands; no public endpoint can create administrator accounts."""

import argparse
import asyncio
import getpass
import re
import secrets
import sys

from sqlalchemy import text

from app.admin.auth import hash_password
from app.core.config import settings
from app.core.security import digest
from app.db.models import AdminUser, Base, InvitationLink
from app.db.session import engine, sessions
from app.schemas import InvitationCreate
from app.services.invitations import create_invitation, invitation_link


async def migrate(runtime_role: str | None = None) -> None:
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))

    def upgrade(connection):
        config.attributes["connection"] = connection
        command.upgrade(config, "head")

    async with engine().connect() as connection:
        await connection.run_sync(upgrade)
    if runtime_role:
        if not re.fullmatch(r"arn:aws:iam::\d{12}:role/[A-Za-z0-9_+=,.@/\-]+", runtime_role):
            raise ValueError("Invalid AWS runtime role ARN")
        async with engine().begin() as connection:
            exists = await connection.scalar(
                text("SELECT 1 FROM pg_roles WHERE rolname = 'wedding_app'")
            )
        if not exists:
            async with engine().begin() as connection:
                await connection.execute(text("CREATE ROLE wedding_app WITH LOGIN"))
        tables = ", ".join(f'"{name}"' for name in Base.metadata.tables if name != "admin_users")
        for statement in [
            "GRANT USAGE ON SCHEMA public TO wedding_app",
            f"GRANT SELECT, INSERT, UPDATE ON TABLE {tables} TO wedding_app",
            "GRANT SELECT, UPDATE (failed_attempts, locked_until, totp_secret, totp_enabled, totp_last_step, version) ON admin_users TO wedding_app",
            "GRANT DELETE ON invitation_messages TO wedding_app",
            f"AWS IAM GRANT wedding_app TO '{runtime_role}'",
        ]:
            async with engine().begin() as connection:
                await connection.execute(text(statement))


async def seed_local() -> None:
    if settings().dsql_host or settings().cookie_secure:
        raise RuntimeError("Demo invitations are only permitted in the local environment")
    async with sessions()() as db:
        for token, name, email, admin in [
            ("DEMO-LOVE-2027", "Dear friends", "guest@example.com", False),
            ("DEMO-ADMIN-2027", "Wedding hosts", "admin@example.com", True),
        ]:
            if not await db.get(InvitationLink, digest(token)):
                await create_invitation(
                    db, InvitationCreate(name=name, email=email), is_admin=admin, token=token
                )
        await db.commit()


async def run() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    migration = sub.add_parser("migrate")
    migration.add_argument("--runtime-role")
    admin = sub.add_parser("create-admin")
    admin.add_argument("--name", required=True)
    admin.add_argument("--email", required=True)
    credentials = sub.add_parser("admin-user", help="Create or reset a SQLAdmin account")
    credentials.add_argument("--username", required=True)
    credentials.add_argument(
        "--reset-mfa",
        action="store_true",
        help="Reset MFA enrollment and revoke existing admin sessions",
    )
    credentials.add_argument(
        "--password-stdin",
        action="store_true",
        help="Read one password line from stdin instead of prompting",
    )
    sub.add_parser("seed-local")
    args = parser.parse_args()
    if args.command == "migrate":
        await migrate(args.runtime_role)
    elif args.command == "seed-local":
        await seed_local()
    elif args.command == "admin-user":
        username = args.username.strip().lower()
        if not re.fullmatch(r"[a-z0-9_.@+-]{3,100}", username):
            parser.error("Username must be 3–100 letters, digits, or _.@+-")
        password = (
            sys.stdin.readline().rstrip("\r\n")
            if args.password_stdin
            else getpass.getpass("New admin password (at least 14 characters): ")
        )
        if not 14 <= len(password) <= 1024:
            parser.error("Use a password between 14 and 1024 characters")
        if not args.password_stdin and password != getpass.getpass("Confirm password: "):
            parser.error("Passwords do not match")
        async with sessions()() as db:
            user = await db.get(AdminUser, username)
            if user is None:
                user = AdminUser(username=username)
                db.add(user)
            if args.reset_mfa:
                user.totp_secret = ""
                user.totp_enabled = False
                user.totp_last_step = -1
            user.password_hash = await asyncio.to_thread(hash_password, password)
            user.version = secrets.token_hex(24)
            user.active = True
            user.failed_attempts = 0
            user.locked_until = 0
            await db.commit()
        print(
            f"Admin account {username!r} is ready. Sign in at {settings().site_url.rstrip('/')}/api/admin/"
        )
    else:
        if settings().cookie_secure or settings().dsql_host:
            raise RuntimeError(
                "Use admin-user for production administrators; invitation admin tokens are local-only"
            )
        async with sessions()() as db:
            invite = await create_invitation(
                db, InvitationCreate(name=args.name, email=args.email), is_admin=True
            )
            await db.commit()
            print(invitation_link(invite))
    await engine().dispose()


if __name__ == "__main__":
    asyncio.run(run())
