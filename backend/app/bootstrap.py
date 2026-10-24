"""Private deployment application, invoked only through Lambda's IAM-protected API."""

import asyncio
import logging
import re
import secrets

import boto3
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.admin.auth import hash_password
from app.core.config import BootstrapSettings
from app.db.models import AdminUser
from app.db.session import sessions
from app.manage import migrate

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


def admin_credentials(config: BootstrapSettings) -> tuple[str, str]:
    username = config.admin_username.strip().lower()
    password = config.admin_password.get_secret_value()
    if not re.fullmatch(r"[a-z0-9_.@+-]{3,100}", username):
        raise ValueError("ADMIN_USERNAME must contain 3–100 letters, digits, or _.@+-")
    if not 14 <= len(password) <= 1024:
        raise ValueError("AdminPassword must contain 14–1024 characters")
    return username, password


async def ensure_admin(username: str, password: str) -> str:
    async with sessions()() as db:
        if await db.get(AdminUser, username) is not None:
            return "existing"
        db.add(
            AdminUser(
                username=username,
                password_hash=await asyncio.to_thread(hash_password, password),
                version=secrets.token_hex(24),
            )
        )
        await db.commit()
    return "created"


def request_ses_access(config: BootstrapSettings) -> str:
    client = boto3.client("sesv2", region_name="eu-central-1")
    account = client.get_account()
    if account.get("ProductionAccessEnabled"):
        return "approved"
    review = account.get("Details", {}).get("ReviewDetails", {}).get("Status")
    if review in {"PENDING", "DENIED", "GRANTED"}:
        return {"PENDING": "pending", "DENIED": "denied", "GRANTED": "review-granted"}[review]
    if review not in {None, "FAILED"}:
        raise RuntimeError("Unrecognized SES review status")
    identity = client.get_email_identity(EmailIdentity=config.ses_identity)
    if not identity.get("VerifiedForSendingStatus"):
        return "identity-unverified"
    try:
        client.put_account_details(
            ProductionAccessEnabled=True,
            MailType="TRANSACTIONAL",
            WebsiteURL=config.site_url,
            AdditionalContactEmailAddresses=[config.wedding_groom_email],
            ContactLanguage="EN",
        )
    except client.exceptions.ConflictException:
        # Another deploy/operator submitted a request after our status check.
        return "pending"
    return "submitted"


@app.get("/api/health")
def health():
    # Adapter readiness must not require an initialized database.
    return {"ready": True}


@app.post("/bootstrap")
async def bootstrap():
    phase = "credentials"
    debug = False
    try:
        config = BootstrapSettings()
        debug = config.debug_deploy
        username, password = admin_credentials(config)
        phase = "migrations"
        await migrate(config.runtime_role_arn)
        phase = "administrator"
        admin = await ensure_admin(username, password)
        phase = "ses"
        ses = await asyncio.to_thread(request_ses_access, config)
    except Exception as exc:
        if debug:
            logging.getLogger(__name__).exception(
                "Deployment initialization failed during %s", phase
            )
            return JSONResponse(
                {"ok": False, "phase": phase, "error": f"{type(exc).__name__}: {exc}"},
                status_code=500,
            )
        logging.getLogger(__name__).error("Deployment initialization failed during %s", phase)
        return JSONResponse({"ok": False}, status_code=500)
    return {"ok": True, "admin": admin, "ses": ses}
