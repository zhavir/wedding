"""QR enrollment is available only after successful password verification."""

import base64
import hmac
import io
import secrets
import time
from html import escape

import qrcode
from sqladmin import BaseView, expose
from starlette.responses import HTMLResponse, RedirectResponse

from app.admin.auth import authenticated_session, failed_attempt
from app.db.models import AdminUser
from app.db.session import sessions
from app.services.totp import authenticator, consume_code


class MfaView(BaseView):
    def is_visible(self, request):
        return False

    @expose("/mfa", methods=["GET", "POST"])
    async def mfa(self, request):
        async with sessions()() as db:
            user = await db.get(AdminUser, request.session.get("mfa_user", ""))
            if not user or user.totp_enabled or user.locked_until > time.time():
                return RedirectResponse(request.url_for("admin:login"), status_code=303)
            error = ""
            if request.method == "POST":
                form = await request.form()
                if not hmac.compare_digest(
                    str(form.get("csrf", "")).encode(),
                    request.session.get("mfa_csrf", "missing").encode(),
                ):
                    return HTMLResponse("Invalid form. Sign in again.", status_code=403)
                if await consume_code(db, user, str(form.get("otp", "")).strip()):
                    user.totp_enabled = True
                    user.version = secrets.token_hex(24)
                    user.failed_attempts = user.locked_until = 0
                    await db.commit()
                    authenticated_session(request, user)
                    return RedirectResponse(request.url_for("admin:index"), status_code=303)
                await failed_attempt(db, user)
                error = "Invalid or expired code. Please try again."
            image = qrcode.make(
                authenticator(user).provisioning_uri(
                    name=user.username, issuer_name="Andrea & Sara Wedding Admin"
                )
            )
            stream = io.BytesIO()
            image.save(stream, format="PNG")
            encoded = base64.b64encode(stream.getvalue()).decode()
            csrf = escape(request.session["mfa_csrf"], quote=True)
            return HTMLResponse(
                f'''<!doctype html><html lang="en"><meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Set up two-factor authentication</title><style>body{{font:18px system-ui;background:#f7f5ef;color:#354b3d;max-width:560px;margin:auto;padding:24px}}img{{width:100%;max-width:320px}}input,button{{font:inherit;padding:12px;box-sizing:border-box;max-width:100%}}</style>
            <h1>Set up two-factor authentication</h1><p>Scan this QR code with Google Authenticator or another TOTP authenticator. Then enter its six-digit code. Setup expires after five minutes.</p>
            <img src="data:image/png;base64,{encoded}" alt="Authenticator setup QR code">
            <p role="alert">{escape(error)}</p><form method="post"><input type="hidden" name="csrf" value="{csrf}">
            <label for="otp">Authenticator code</label><input id="otp" name="otp" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{{6}}" maxlength="6" required>
            <button>Enable two-factor authentication</button></form><p>The trusted operator CLI can reset MFA if your phone is lost.</p></html>''',
                headers={
                    "Cache-Control": "no-store",
                    "X-Frame-Options": "DENY",
                    "Referrer-Policy": "no-referrer",
                },
            )
