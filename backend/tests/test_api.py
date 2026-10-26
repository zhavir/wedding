import inspect
import io
from unittest.mock import MagicMock

import pytest
from app.core.config import settings
from app.db.models import Guest
from app.db.session import engine, sessions
from app.main import app
from app.manage import migrate
from app.schemas import InvitationCreate
from app.services.invitations import create_invitation
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from PIL import Image


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("INVITE_ENCRYPTION_KEY", "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8=")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    monkeypatch.setenv("WEDDING_GROOM_NAME", "Example groom")
    monkeypatch.setenv("WEDDING_GROOM_EMAIL", "groom@example.test")
    monkeypatch.setenv("WEDDING_BRIDE_NAME", "Example bride")
    monkeypatch.setenv("WEDDING_BRIDE_EMAIL", "bride@example.test")
    settings.cache_clear()
    engine.cache_clear()
    sessions.cache_clear()

    async def seed():
        await migrate()
        async with sessions()() as db:
            await create_invitation(
                db,
                InvitationCreate(name="Guest", email="guest@example.com", language="en"),
                token="GUEST-CODE-123",
            )
            await create_invitation(
                db,
                InvitationCreate(name="Host", email="host@example.com"),
                token="ADMIN-CODE-123",
                is_admin=True,
            )
            await db.commit()

    with TestClient(
        app, base_url="http://testserver", headers={"Origin": "http://localhost:5173"}
    ) as test:
        assert test.portal is not None
        test.portal.call(seed)
        yield test
        test.portal.call(engine().dispose)
    sessions.cache_clear()
    engine.cache_clear()
    settings.cache_clear()


@pytest.fixture(autouse=True)
def aws(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "ses-local")
    storage = MagicMock()
    storage.create_multipart_upload.return_value = {"UploadId": "multipart-test"}
    storage.generate_presigned_post.return_value = {"url": "http://s3", "fields": {}}
    storage.generate_presigned_url.return_value = "https://example.com/signed"
    mail = MagicMock()
    mail.send_email.return_value = {"MessageId": "message-123"}
    mail.send_raw_email.return_value = {"MessageId": "raw-message-123"}
    monkeypatch.setattr("app.routers.photos.s3", lambda public=False: storage)
    monkeypatch.setattr("app.services.photos.s3", lambda public=False: storage)
    monkeypatch.setattr("app.services.uploads.s3", lambda public=False: storage)
    monkeypatch.setattr("app.services.mail_transport.ses", lambda: mail)
    return storage, mail


def test_health_checks_database_and_reuses_connection(client):
    from sqlalchemy import event

    queries = []
    connections = []
    pool = engine().sync_engine

    def record_query(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)

    def record_checkout(connection, record, proxy):
        connections.append(connection)

    event.listen(pool, "before_cursor_execute", record_query)
    event.listen(pool, "checkout", record_checkout)
    try:
        for _ in range(2):
            response = client.get("/api/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
        assert queries == ["SELECT 1", "SELECT 1"]
        assert len(connections) == 2
        assert connections[0] is connections[1]
    finally:
        event.remove(pool, "before_cursor_execute", record_query)
        event.remove(pool, "checkout", record_checkout)


def test_health_reports_database_failure(client, monkeypatch):
    from sqlalchemy.exc import OperationalError
    from sqlalchemy.ext.asyncio import AsyncSession

    async def unavailable(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("private database details"))

    monkeypatch.setattr(AsyncSession, "execute", unavailable)
    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.headers["Retry-After"] == "1"
    assert "private database details" not in response.text


def login(client, code="GUEST-CODE-123"):
    response = client.post("/api/session", json={"code": code})
    assert response.status_code == 200
    return response


def body(**overrides):
    return {
        "email": "guest@example.com",
        "attending": True,
        "guests": [{"name": "Guest", "dietary": ""}],
        "message": "",
        "consent": True,
        **overrides,
    }


def test_every_endpoint_is_async():
    assert all(
        inspect.iscoroutinefunction(route.endpoint)
        for route in app.routes
        if isinstance(route, APIRoute)
    )


def test_cookie_is_persistent_and_not_in_json(client):
    response = login(client)
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Max-Age=34560000" in cookie
    assert "token" not in response.json()
    assert client.get("/api/session").json()["name"] == "Guest"
    assert "set-cookie" in client.get("/api/session").headers


def test_logout_revokes_server_session(client):
    login(client)
    token = client.cookies.get("wedding_session")
    client.delete("/api/session")
    assert client.get("/api/session").status_code == 401
    assert (
        client.get("/api/session", headers={"cookie": f"wedding_session={token}"}).status_code
        == 401
    )


def test_unauthorized_and_csrf(client):
    assert client.get("/api/photos").status_code == 401
    assert client.get("/api/admin/invitations").status_code == 401
    login(client)
    assert client.get("/api/admin/invitations").status_code == 403
    assert (
        client.put("/api/rsvp", json=body(), headers={"origin": "https://evil.example"}).status_code
        == 403
    )


def test_rsvp_storage(client):
    login(client)
    assert client.put("/api/rsvp", json=body()).status_code == 200
    assert client.get("/api/rsvp").json()["rsvp"] == body()
    assert client.put("/api/rsvp", json=body(attending=False, guests=[])).status_code == 200


@pytest.mark.parametrize(
    "overrides",
    [
        {"email": "invalid"},
        {"consent": False},
        {"guests": []},
        {"guests": [{"name": " "}]},
        {"attending": False},
        {"message": "x" * 1001},
        {"extra": "bad"},
        {"guests": [{"name": "Guest"}] * 3},
    ],
)
def test_invalid_rsvp(client, overrides):
    login(client)
    assert client.put("/api/rsvp", json=body(**overrides)).status_code == 422


def test_generate_preview_send_and_revoke(client, aws):
    _, mail = aws
    login(client, "ADMIN-CODE-123")
    result = client.post(
        "/api/admin/invitations",
        json={
            "invitations": [
                {
                    "name": "Alex <script>alert(1)</script>",
                    "email": "alex@example.com",
                    "max_guests": 2,
                }
            ]
        },
    )
    assert result.status_code == 201
    invitation = result.json()["items"][0]
    mail.send_email.assert_not_called()
    preview = client.get(f"/api/admin/invitations/{invitation['id']}/preview").json()
    assert "<script>" not in preview["html"]
    assert "viewport" in preview["html"] and invitation["link"] in preview["html"]
    payload = {"ids": [invitation["id"]]}
    assert (
        client.post("/api/admin/invitations/send", json=payload).json()["results"][0]["status"]
        == "sent"
    )
    assert (
        client.post("/api/admin/invitations/send", json=payload).json()["results"][0]["status"]
        == "skipped"
    )
    assert mail.send_email.call_count == 1
    code = invitation["link"].split("#invite=")[1]
    guest_cookie = (
        client.post("/api/session", json={"code": code}).headers["set-cookie"].split(";")[0]
    )
    login(client, "ADMIN-CODE-123")
    client.post(f"/api/admin/invitations/{invitation['id']}/revoke")
    assert client.get("/api/session", headers={"cookie": guest_cookie}).status_code == 401


def test_admin_privilege_cannot_be_requested(client):
    login(client, "ADMIN-CODE-123")
    assert (
        client.post(
            "/api/admin/invitations",
            json={"invitations": [{"name": "Bad", "email": "bad@example.com", "is_admin": True}]},
        ).status_code
        == 422
    )


def test_original_bytes_and_preview(client, aws):
    storage, _ = aws
    login(client)
    buf = io.BytesIO()
    Image.new("RGB", (1800, 1200), (24, 66, 88)).save(buf, "JPEG", quality=98)
    original = buf.getvalue()
    upload = client.post(
        "/api/photos/upload",
        json={
            "filename": "photo.jpg",
            "content_type": "image/jpeg",
            "size": len(original),
            "consent": True,
        },
    ).json()
    assert [
        "content-length-range",
        len(original),
        len(original),
    ] in storage.generate_presigned_post.call_args.kwargs["Conditions"]
    storage.get_object.return_value = {"ContentLength": len(original), "Body": io.BytesIO(original)}
    assert client.post(f"/api/photos/{upload['id']}/complete").status_code == 200
    calls = storage.put_object.call_args_list
    assert calls[0].kwargs["Body"] == original and calls[0].kwargs["IfNoneMatch"] == "*"
    with Image.open(io.BytesIO(calls[1].kwargs["Body"])) as preview:
        assert preview.format == "WEBP" and max(preview.size) <= 1200
    assert client.post(f"/api/photos/{upload['id']}/complete").status_code == 200
    assert client.get("/api/photos").json()["items"] == []

    async def publish(value):
        import hashlib

        from app.db.models import Photo

        async with sessions()() as db:
            photo = await db.get(Photo, upload["id"])
            assert photo is not None
            assert photo.original_filename == "photo.jpg"
            assert photo.uploader_name
            assert photo.owner
            assert 0 < photo.uploaded_at <= photo.completed_at
            assert (photo.width, photo.height) == (1800, 1200)
            assert photo.sha256 == hashlib.sha256(original).hexdigest()
            assert photo.codec.lower() == "jpeg"
            photo.gallery_visible = value
            await db.commit()

    client.portal.call(publish, True)
    assert len(client.get("/api/photos").json()["items"]) == 1
    client.portal.call(publish, False)
    assert client.get("/api/photos").json()["items"] == []


@pytest.mark.parametrize(
    "kind,size", [("image/svg+xml", 10), ("image/jpeg", 0), ("image/png", 26 * 1024 * 1024)]
)
def test_invalid_upload(client, aws, kind, size):
    login(client)
    assert (
        client.post(
            "/api/photos/upload",
            json={"filename": "file", "content_type": kind, "size": size, "consent": True},
        ).status_code
        == 422
    )


def test_other_guest_cannot_complete_upload(client, aws):
    login(client)
    photo = client.post(
        "/api/photos/upload",
        json={"filename": "x.jpg", "content_type": "image/jpeg", "size": 5, "consent": True},
    ).json()
    login(client, "ADMIN-CODE-123")
    assert client.post(f"/api/photos/{photo['id']}/complete").status_code == 404


def test_invalid_image_not_gallery_visible(client, aws):
    storage, _ = aws
    login(client)
    photo = client.post(
        "/api/photos/upload",
        json={"filename": "x.jpg", "content_type": "image/jpeg", "size": 5, "consent": True},
    ).json()
    storage.get_object.return_value = {"ContentLength": 5, "Body": io.BytesIO(b"hello")}
    assert client.post(f"/api/photos/{photo['id']}/complete").status_code == 422
    storage.put_object.assert_not_called()


def admin_login(client):
    from app.admin.auth import hash_password
    from app.db.models import AdminUser

    async def seed_admin():
        async with sessions()() as db:
            db.add(
                AdminUser(
                    username="organiser",
                    password_hash=hash_password("testing-password-long"),
                    version="test-version",
                    totp_secret=__import__("app.core.security", fromlist=["cipher"])
                    .cipher()
                    .encrypt(b"JBSWY3DPEHPK3PXP")
                    .decode(),
                    totp_enabled=True,
                    active=True,
                )
            )
            await db.commit()

    client.portal.call(seed_admin)
    return client.post(
        "/api/admin/login",
        data={
            "username": "organiser",
            "password": "testing-password-long",
            "otp": __import__("pyotp").TOTP("JBSWY3DPEHPK3PXP").now(),
        },
    )


def test_production_rejects_legacy_invitation_admin_api(client, monkeypatch):
    login(client, "ADMIN-CODE-123")
    monkeypatch.setenv("COOKIE_SECURE", "true")
    settings.cache_clear()
    response = client.get("/api/admin/invitations")
    assert response.status_code == 403
    assert "two-factor" in response.json()["detail"]


def test_sqladmin_requires_separate_credentials(client):
    login(client, "ADMIN-CODE-123")
    response = client.get("/api/admin/invitation/list", follow_redirects=False)
    assert response.status_code == 302
    assert "/api/admin/login" in response.headers["location"]
    response = admin_login(client)
    assert response.status_code == 200
    assert "Invitations" in response.text
    assert client.cookies.get("wedding_admin")
    assert (
        "httponly"
        in "".join(
            item.headers.get("set-cookie", "") for item in [*response.history, response]
        ).lower()
    )


def test_sqladmin_create_review_send_and_replay(client, aws):
    import re

    _, mail = aws

    def extract(pattern, value):
        match = re.search(pattern, value)
        assert match is not None
        return match.group(1)

    admin_login(client)
    assert (
        client.post(
            "/api/admin/guest/create",
            data={
                "name": "Admin created guest",
                "email": "created@example.com",
                "audience": "guest",
                "save": "Save",
            },
        ).status_code
        == 200
    )

    async def find_guest():
        from app.db.models import Guest
        from sqlalchemy import select

        async with sessions()() as db:
            return await db.scalar(select(Guest.id).where(Guest.name == "Admin created guest"))

    guest_id = client.portal.call(find_guest)
    response = client.post(
        "/api/admin/invitation/create",
        data={
            "guest": guest_id,
            "language": "en",
            "max_guests": "2",
            "active": "y",
            "save": "Save",
        },
    )
    assert response.status_code == 200
    assert mail.send_email.call_count == 0

    async def find_invitation():
        from app.db.models import Invitation
        from sqlalchemy import select

        async with sessions()() as db:
            return await db.scalar(
                select(Invitation).where(Invitation.guest.has(Guest.email == "created@example.com"))
            )

    invite = client.portal.call(find_invitation)
    assert invite is not None and invite.encrypted_token and not invite.is_admin
    review = client.get(f"/api/admin/invitation/action/send-invitations?pks={invite.id}")
    assert review.status_code == 200
    assert mail.send_email.call_count == 0
    token = extract(r'name="csrf" value="([^"]+)"', review.text)
    action_url = extract(r'<form method="post" action="([^"]+)"', review.text)
    assert client.post(action_url, data={"csrf": "wrong"}).status_code == 403
    review = client.get(f"/api/admin/invitation/action/send-invitations?pks={invite.id}")
    token = extract(r'name="csrf" value="([^"]+)"', review.text)
    result = client.post(action_url, data={"csrf": token})
    assert result.status_code == 200 and "sent" in result.text
    assert mail.send_email.call_count == 1
    assert client.post(action_url, data={"csrf": token}).status_code == 403
    review = client.get(f"/api/admin/invitation/action/send-invitations?pks={invite.id}")
    token = extract(r'name="csrf" value="([^"]+)"', review.text)
    client.post(action_url, data={"csrf": token})
    assert mail.send_email.call_count == 1


def test_sqladmin_rejects_cross_origin_and_password_reset_invalidates_session(client):
    admin_login(client)
    response = client.post(
        "/api/admin/invitation/create", data={}, headers={"Origin": "https://attacker.example"}
    )
    assert response.status_code == 403

    async def reset():
        from app.db.models import AdminUser

        async with sessions()() as db:
            user = await db.get(AdminUser, "organiser")
            assert user is not None
            user.version = "reset-version"
            await db.commit()

    client.portal.call(reset)
    assert client.get("/api/admin/invitation/list", follow_redirects=False).status_code == 302


def test_admin_cli_creates_and_resets_a_login(client):
    import re
    import subprocess
    import sys

    from app.services.totp import authenticator

    async def enrollment_code():
        from app.db.models import AdminUser

        async with sessions()() as db:
            user = await db.get(AdminUser, "cli-admin")
            assert user is not None
            return authenticator(user).now()

    command = [
        sys.executable,
        "-m",
        "app.manage",
        "admin-user",
        "--username",
        "cli-admin",
        "--password-stdin",
    ]
    result = subprocess.run(
        command, input="cli-initial-password-long\n", text=True, capture_output=True, check=True
    )
    assert "cli-initial-password-long" not in result.stdout + result.stderr
    response = client.post(
        "/api/admin/login", data={"username": "cli-admin", "password": "cli-initial-password-long"}
    )
    assert "Set up two-factor authentication" in response.text
    assert "data:image/png;base64," in response.text
    assert client.get("/api/admin/invitation/list", follow_redirects=False).status_code == 302
    match = re.search(r'name="csrf" value="([^"]+)"', response.text)
    assert match is not None
    csrf = match.group(1)
    assert client.post("/api/admin/mfa", data={"csrf": "wrong", "otp": "000000"}).status_code == 403
    code = client.portal.call(enrollment_code)
    response = client.post("/api/admin/mfa", data={"csrf": csrf, "otp": code})
    assert "Invitations" in response.text
    # The same authenticator code cannot establish a second session.
    assert (
        client.post(
            "/api/admin/login",
            data={"username": "cli-admin", "password": "cli-initial-password-long", "otp": code},
        ).status_code
        == 400
    )
    subprocess.run(
        [*command, "--reset-mfa"],
        input="cli-replacement-password-long\n",
        text=True,
        capture_output=True,
        check=True,
    )
    assert client.get("/api/admin/invitation/list", follow_redirects=False).status_code == 302
    assert (
        client.post(
            "/api/admin/login",
            data={"username": "cli-admin", "password": "cli-initial-password-long"},
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/admin/login",
            data={"username": "cli-admin", "password": "cli-replacement-password-long"},
        ).status_code
        == 200
    )


def test_admin_forms_keep_same_origin_and_reject_null_origin(client):
    assert client.get("/api/admin/login").headers["referrer-policy"] == "same-origin"
    assert (
        client.post(
            "/api/admin/login",
            headers={"Origin": "null"},
            data={"username": "host", "password": "example"},
        ).status_code
        == 403
    )


def invitation_code(client):
    from app.core.security import cipher
    from app.db.models import Invitation, InvitationAccess
    from sqlalchemy import select

    async def read():
        async with sessions()() as db:
            invite = await db.scalar(
                select(Invitation).where(Invitation.guest.has(Guest.email == "guest@example.com"))
            )
            assert invite is not None
            access = await db.get(InvitationAccess, invite.id)
            assert access is not None
            return cipher().decrypt(access.encrypted_code.encode()).decode()

    return client.portal.call(read)


def test_short_code_authenticates_for_rsvp_and_photos(client):
    code = invitation_code(client)
    assert len(code) == 11 and code[5] == "-"
    response = login(client, code.lower().replace("-", " "))
    assert response.status_code == 200
    assert client.get("/api/rsvp").status_code == 200
    assert client.get("/api/photos").status_code == 200


def test_recovery_is_private_throttled_and_rotates_only_after_use(client, aws):
    import re

    _, mail = aws
    original = invitation_code(client)
    unknown = client.post("/api/session/recover", json={"email": "unknown@example.com"})
    known = client.post("/api/session/recover", json={"email": "guest@example.com"})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert mail.send_email.call_count == 1
    assert mail.send_email.call_args.kwargs["Destination"] == {"ToAddresses": ["guest@example.com"]}
    content = mail.send_email.call_args.kwargs["Message"]["Body"]["Text"]["Data"]
    match = re.search(r"Codice invito: ([A-Z2-9]{5}-[A-Z2-9]{5})", content)
    assert match is not None
    replacement = match.group(1)
    assert replacement != original
    assert (
        client.post("/api/session/recover", json={"email": "guest@example.com"}).status_code == 202
    )
    assert mail.send_email.call_count == 1
    assert login(client, original).status_code == 200
    assert login(client, replacement).status_code == 200
    assert client.post("/api/session", json={"code": original}).status_code == 401
    assert client.post("/api/session", json={"code": "GUEST-CODE-123"}).status_code == 401
    assert login(client, replacement).status_code == 200


def test_recovery_link_and_expired_replacement(client, aws):
    import re

    from app.db.models import InvitationAccess
    from sqlalchemy import select

    _, mail = aws
    original = invitation_code(client)
    client.post("/api/session/recover", json={"email": "guest@example.com"})
    content = mail.send_email.call_args.kwargs["Message"]["Body"]["Text"]["Data"]
    match = re.search(r"#invite=([A-Za-z0-9_-]+)", content)
    assert match is not None
    replacement = match.group(1)

    async def expire():
        async with sessions()() as db:
            row = await db.scalar(
                select(InvitationAccess).where(InvitationAccess.pending_link_hash.is_not(None))
            )
            assert row is not None
            row.pending_expires = 1
            await db.commit()

    client.portal.call(expire)
    assert client.post("/api/session", json={"code": replacement}).status_code == 401
    assert login(client, original).status_code == 200


def test_recovery_does_not_send_for_admin_and_is_rate_limited(client, aws):
    _, mail = aws
    for _ in range(5):
        assert (
            client.post("/api/session/recover", json={"email": "host@example.com"}).status_code
            == 202
        )
    assert mail.send_email.call_count == 0
    assert (
        client.post("/api/session/recover", json={"email": "host@example.com"}).status_code == 429
    )


def test_recovery_link_activates_replacement_and_invalidates_previous_link(client, aws):
    import re

    _, mail = aws
    original = invitation_code(client)
    assert (
        client.post("/api/session/recover", json={"email": "guest@example.com"}).status_code == 202
    )
    content = mail.send_email.call_args.kwargs["Message"]["Body"]["Text"]["Data"]
    match = re.search(r"#invite=([A-Za-z0-9_-]+)", content)
    assert match is not None
    assert login(client, match.group(1)).status_code == 200
    assert client.get("/api/photos").status_code == 200
    assert client.post("/api/session", json={"code": original}).status_code == 401
    assert client.post("/api/session", json={"code": "GUEST-CODE-123"}).status_code == 401
    assert login(client, invitation_code(client)).status_code == 200


def test_recovery_delivery_failure_keeps_existing_invitation_usable(client, aws):
    from botocore.exceptions import ClientError

    _, mail = aws
    original = invitation_code(client)
    mail.send_email.side_effect = ClientError(
        {"Error": {"Code": "MessageRejected", "Message": "Test delivery failure"}}, "SendEmail"
    )
    response = client.post("/api/session/recover", json={"email": "guest@example.com"})
    assert response.status_code == 202
    assert login(client, original).status_code == 200
    assert login(client, "GUEST-CODE-123").status_code == 200


def test_link_only_invitation_and_italian_email(client, aws):
    _, mail = aws
    login(client, "ADMIN-CODE-123")
    response = client.post(
        "/api/admin/invitations", json={"invitations": [{"name": "Amici", "language": "it"}]}
    )
    assert response.status_code == 201
    invite = response.json()["items"][0]
    preview = client.get(f"/api/admin/invitations/{invite['id']}/preview").json()
    assert '<html lang="it">' in preview["html"]
    assert "Siete invitati" in preview["subject"]
    assert "Aprite la galleria fotografica" in preview["html"]
    assert "YOU’RE INVITED" not in preview["html"]
    assert (
        client.post("/api/admin/invitations/send", json={"ids": [invite["id"]]}).json()["results"][
            0
        ]["status"]
        == "skipped"
    )
    mail.send_email.assert_not_called()
    login(client, invite["link"].split("#invite=")[1])
    assert client.get("/api/rsvp").json()["prefill"] == {"name": "Amici", "email": ""}
    assert client.put("/api/rsvp", json=body()).status_code == 200


def test_structured_rsvp_and_notification_failure_preserve_response(client, aws, monkeypatch):
    from app.db.models import Invitation, RSVPNotification
    from botocore.exceptions import ClientError
    from sqlalchemy import select

    monkeypatch.setattr(settings(), "rsvp_notification_email", "hosts@example.com")
    _, mail = aws
    mail.send_email.side_effect = ClientError(
        {"Error": {"Code": "MessageRejected", "Message": "Test rejection"}}, "SendEmail"
    )
    login(client)
    assert client.get("/api/rsvp").json()["prefill"] == {
        "name": "Guest",
        "email": "guest@example.com",
    }
    assert client.put("/api/rsvp", json=body()).status_code == 200
    assert client.get("/api/rsvp").json()["rsvp"] == body()

    async def inspect_rows():
        async with sessions()() as db:
            response = await db.scalar(select(Invitation).where(Invitation.has_rsvp.is_(True)))
            assert response is not None
            guest = response.guest
            notification = await db.scalar(select(RSVPNotification))
            assert response and response.attending and response.consent
            assert guest and guest.name == "Guest"
            assert notification and notification.status == "failed"
            assert notification.recipient == "hosts@example.com"

    client.portal.call(inspect_rows)
    assert mail.send_email.call_count == 1
    assert client.put("/api/rsvp", json=body()).status_code == 200
    assert mail.send_email.call_count == 1  # An HTTP retry does not send twice.
    mail.send_email.side_effect = None
    declined = body(attending=False, guests=[])
    assert client.put("/api/rsvp", json=declined).status_code == 200
    assert client.get("/api/rsvp").json()["rsvp"] == declined
    assert mail.send_email.call_count == 2

    async def inspect_decline():
        async with sessions()() as db:
            invite = await db.scalar(select(Invitation).where(Invitation.has_rsvp.is_(True)))
            assert invite and invite.attending is False and invite.response_guests == "[]"
            assert invite.guest.name == "Guest"
            assert await db.scalar(
                select(RSVPNotification).where(RSVPNotification.status == "sent")
            )

    client.portal.call(inspect_decline)


def test_alembic_migrations_are_idempotent_and_match_models(client):
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from app.db.models import Base
    from app.migrations.schema import compare_server_default
    from sqlalchemy import text

    async def check():
        await migrate()
        await migrate()
        async with engine().connect() as connection:
            assert (
                await connection.scalar(text("SELECT version_num FROM alembic_version"))
                == "0008_align_schema_defaults"
            )
            assert await connection.scalar(text("SELECT count(*) FROM invitation_messages")) == 16
            differences = await connection.run_sync(
                lambda sync: compare_metadata(
                    MigrationContext.configure(
                        sync, opts={"compare_server_default": compare_server_default}
                    ),
                    Base.metadata,
                )
            )
            assert differences == []

    client.portal.call(check)


def test_witness_invitation_and_response(client, aws):
    login(client, "ADMIN-CODE-123")
    invitation = client.post(
        "/api/admin/invitations",
        json={
            "invitations": [
                {
                    "name": "Testimone",
                    "email": "witness@example.com",
                    "language": "it",
                    "is_witness": True,
                }
            ]
        },
    ).json()["items"][0]
    preview = client.get(f"/api/admin/invitations/{invitation['id']}/preview").json()
    assert "testimone" in preview["subject"]
    assert "testimone" in preview["html"]
    login(client, invitation["link"].split("#invite=")[1])
    assert client.get("/api/session").json()["is_witness"] is True
    assert client.put("/api/rsvp", json=body()).status_code == 422
    response = body(witness_acceptance=True)
    assert client.put("/api/rsvp", json=response).status_code == 200
    assert client.get("/api/rsvp").json()["rsvp"]["witness_acceptance"] is True
    assert aws[1].send_raw_email.call_count == 1
    assert client.put("/api/rsvp", json=response).status_code == 200
    assert aws[1].send_raw_email.call_count == 1


def test_confirmation_calendar_and_delivery_failure(client, aws):
    from email import policy
    from email.parser import BytesParser

    from app.db.models import ConfirmationEmail
    from botocore.exceptions import ClientError
    from sqlalchemy import select

    login(client)
    assert client.put("/api/rsvp", json=body(witness_acceptance=True)).status_code == 422
    assert client.put("/api/rsvp", json=body()).status_code == 200
    mail = aws[1]
    raw = mail.send_raw_email.call_args.kwargs
    assert raw["Destinations"] == ["guest@example.com"]
    message = BytesParser(policy=policy.default).parsebytes(raw["RawMessage"]["Data"])
    assert "Thank you" in message["Subject"]
    attachments = list(message.iter_attachments())
    assert len(attachments) == 1
    attachment = attachments[0]
    assert attachment.get_content_type() == "text/calendar"
    payload = attachment.get_payload(decode=True)
    assert isinstance(payload, bytes)
    from app.services.confirmations import calendar_attachment

    assert payload == calendar_attachment("en")
    calendar = payload.decode()
    assert "DTSTART:20270520T140000Z\r\n" in calendar
    assert "DTEND:20270520T220000Z\r\n" in calendar
    assert "#invite=" not in calendar
    assert all(len(line.encode()) <= 75 for line in calendar.split("\r\n"))
    assert client.put("/api/rsvp", json=body(message="Updated details")).status_code == 200
    assert mail.send_raw_email.call_count == 1
    assert client.put("/api/rsvp", json=body(attending=False, guests=[])).status_code == 200
    mail.send_raw_email.side_effect = ClientError(
        {"Error": {"Code": "MessageRejected"}}, "SendRawEmail"
    )
    assert client.put("/api/rsvp", json=body()).status_code == 200
    assert client.get("/api/rsvp").json()["rsvp"]["attending"] is True

    async def inspect_failure():
        async with sessions()() as db:
            assert await db.scalar(
                select(ConfirmationEmail).where(ConfirmationEmail.status == "failed")
            )

    client.portal.call(inspect_failure)


def test_calendar_assets_preserve_unicode_and_line_limits():
    from app.services.confirmations import calendar_attachment

    for language in ("en", "it"):
        calendar = calendar_attachment(language).decode("utf-8")
        assert "BEGIN:VCALENDAR\r\n" in calendar
        assert all(len(line.encode()) <= 75 for line in calendar.split("\r\n"))


def test_message_selection_language_stability_and_validation(client, monkeypatch, aws):
    import pytest
    from app.db.models import InvitationMessage
    from app.services.messages import validate_message
    from sqlalchemy import select

    for text in ["{name.__class__}", "{name!r}", "{unknown}", "{name:>5}", "broken {"]:
        with pytest.raises(ValueError):
            validate_message(text)
    login(client, "ADMIN-CODE-123")
    invite = client.post(
        "/api/admin/invitations",
        json={
            "invitations": [
                {"name": "<script>Guest</script>", "language": "it", "email": "italian@example.com"}
            ]
        },
    ).json()["items"][0]
    preview = client.get(f"/api/admin/invitations/{invite['id']}/preview").json()
    assert "<script>Guest</script>" in preview["text"]
    assert "<script>" not in preview["html"]
    assert client.get(f"/api/admin/invitations/{invite['id']}/preview").json() == preview

    async def check_selection():
        async with sessions()() as db:
            rows = list(await db.scalars(select(InvitationMessage)))
            assert {row.language for row in rows} == {"it", "en"}

    client.portal.call(check_selection)
    sent = client.post("/api/admin/invitations/send", json={"ids": [invite["id"]]})
    assert sent.status_code == 200
    assert aws[1].send_email.call_args.kwargs["Message"]["Body"]["Text"]["Data"] == preview["text"]


@pytest.mark.parametrize("paired", [False, True])
def test_video_and_live_photo_originals_are_private(client, aws, tmp_path, paired):
    import subprocess

    storage, _ = aws
    video_file = tmp_path / "clip.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=128x128:d=1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-threads",
            "1",
            str(video_file),
        ],
        check=True,
        timeout=20,
    )
    video = video_file.read_bytes()
    still = io.BytesIO()
    Image.new("RGB", (120, 80)).save(still, "JPEG")
    original = still.getvalue() if paired else video
    login(client)
    payload = {
        "filename": "memory",
        "content_type": "image/jpeg" if paired else "video/mp4",
        "size": len(original),
        "consent": True,
    }
    if paired:
        payload.update(motion_size=len(video), motion_content_type="video/mp4")
    result = client.post("/api/photos/upload", json=payload)
    assert result.status_code == 200
    upload = result.json()
    objects = [{"ContentLength": len(original), "Body": io.BytesIO(original)}]
    if paired:
        objects.append({"ContentLength": len(video), "Body": io.BytesIO(video)})
        assert upload["motion_upload"]
    storage.get_object.side_effect = objects
    assert client.post(f"/api/photos/{upload['id']}/complete").status_code == 200
    stored = {call.kwargs["Key"]: call.kwargs["Body"] for call in storage.put_object.call_args_list}
    assert (
        stored[f"originals/guests/Guest/{upload['id']}-memory{'.jpg' if paired else '.mp4'}"]
        == original
    )
    if paired:
        assert stored[f"originals/guests/Guest/{upload['id']}-motion-memory.mp4"] == video
    with Image.open(io.BytesIO(stored[f"previews/guests/Guest/{upload['id']}.webp"])) as preview:
        assert preview.format == "WEBP"
    assert client.get("/api/photos").json()["items"] == []


def test_heic_original_and_webp_preview(client, aws):
    from pillow_heif import register_heif_opener

    register_heif_opener()
    storage, _ = aws
    original = io.BytesIO()
    Image.new("RGB", (120, 80)).save(original, "HEIF")
    data = original.getvalue()
    login(client)
    upload = client.post(
        "/api/photos/upload",
        json={
            "filename": "live.heic",
            "content_type": "image/heic",
            "size": len(data),
            "consent": True,
        },
    ).json()
    storage.get_object.return_value = {"ContentLength": len(data), "Body": io.BytesIO(data)}
    assert client.post(f"/api/photos/{upload['id']}/complete").status_code == 200
    assert storage.put_object.call_args_list[0].kwargs["Body"] == data
    assert storage.put_object.call_args_list[0].kwargs["Key"] == (
        f"originals/guests/Guest/{upload['id']}-live.heic"
    )


def test_wrong_video_content_and_incomplete_live_pair_rejected(client, aws):
    storage, _ = aws
    login(client)
    payload = {"filename": "bad.mp4", "content_type": "video/mp4", "size": 4, "consent": True}
    upload = client.post("/api/photos/upload", json=payload).json()
    storage.get_object.return_value = {"ContentLength": 4, "Body": io.BytesIO(b"fake")}
    assert client.post(f"/api/photos/{upload['id']}/complete").status_code == 422
    assert not storage.put_object.called
    payload.update(content_type="image/jpeg", motion_size=5)
    assert client.post("/api/photos/upload", json=payload).status_code == 422


def test_invitation_message_witness_language_and_empty_pool(client, monkeypatch):
    from app.db.models import Invitation, InvitationMessage
    from app.services.messages import invitation_message
    from sqlalchemy import update

    async def check():
        async with sessions()() as db:
            invite = Invitation(
                id="test-message",
                name="Guest",
                guest=Guest(name="Guest", language="en", audience="witness"),
                max_guests=1,
                is_witness=True,
            )
            selected = await invitation_message(db, invite)
            assert selected and "witness" in selected
            invite.guest.language = "it"
            selected = await invitation_message(db, invite)
            assert selected and "testimone" in selected
            await db.execute(update(InvitationMessage).values(active=False))
            invite.id = "empty-pool"
            assert await invitation_message(db, invite) is None

    client.portal.call(check)


def test_additional_guest_invitation_lifecycle(client, aws):
    from app.core.security import cipher
    from app.db.models import Invitation
    from sqlalchemy import select

    _, mail = aws
    login(client)
    parent_id = client.get("/api/session").json()["id"]
    party = body(
        guests=[
            {"name": "Guest"},
            {"name": "Alex", "email": "alex@example.com", "dietary": "Vegetarian"},
        ]
    )
    assert client.put("/api/rsvp", json=party).status_code == 200

    async def children():
        async with sessions()() as db:
            rows = (
                await db.scalars(
                    select(Invitation).where(Invitation.parent_invitation_id == parent_id)
                )
            ).all()
            return [
                {
                    "id": row.id,
                    "active": row.active,
                    "name": row.name,
                    "email": row.guest.email,
                    "max_guests": row.max_guests,
                    "code": cipher().decrypt(row.encrypted_token.encode()).decode(),
                }
                for row in rows
            ]

    child = client.portal.call(children)[0]
    assert child["active"] and child["max_guests"] == 1
    assert any(
        call.kwargs["Destination"]["ToAddresses"] == ["alex@example.com"]
        for call in mail.send_email.call_args_list
    )
    count = mail.send_email.call_count
    assert client.put("/api/rsvp", json=party).status_code == 200
    assert mail.send_email.call_count == count
    assert client.get("/api/rsvp").json()["rsvp"]["guests"][1]["email"] == "alex@example.com"
    login(client, child["code"])
    assert client.get("/api/photos").status_code == 200
    old_cookie = client.cookies.get("wedding_session")
    login(client)
    assert client.put("/api/rsvp", json=body(attending=False, guests=[])).status_code == 200
    assert client.portal.call(children)[0]["active"] is False
    assert (
        client.get("/api/photos", headers={"Cookie": f"wedding_session={old_cookie}"}).status_code
        == 401
    )
    assert client.post("/api/session", json={"code": child["code"]}).status_code == 401
    login(client)
    assert client.put("/api/rsvp", json=party).status_code == 200
    records = client.portal.call(children)
    assert len(records) == 1 and records[0]["id"] == child["id"] and records[0]["active"]
    party["guests"][1]["email"] = "new-alex@example.com"
    assert client.put("/api/rsvp", json=party).status_code == 200
    records = client.portal.call(children)
    active = [row for row in records if row["active"]]
    assert len(records) == 2 and len(active) == 1
    assert active[0]["email"] == "new-alex@example.com"
    login(client, active[0]["code"])
    assert (
        client.put(
            "/api/rsvp", json=body(email="new-alex@example.com", attending=False, guests=[])
        ).status_code
        == 200
    )
    assert any(row["active"] for row in client.portal.call(children))
    login(client)
    # Removing only the additional attendee also expires their invitation.
    assert client.put("/api/rsvp", json=body()).status_code == 200
    assert all(not row["active"] for row in client.portal.call(children))


@pytest.mark.parametrize("email", ["guest@example.com", "invalid"])
def test_additional_guest_requires_distinct_valid_email(client, email):
    login(client)
    person = {"name": "Alex"}
    if email is not None:
        person["email"] = email
    assert client.put("/api/rsvp", json=body(guests=[{"name": "Guest"}, person])).status_code == 422


@pytest.mark.parametrize("email_fields", [{}, {"email": None}, {"email": ""}, {"email": "   "}])
def test_additional_guest_without_email(client, aws, email_fields):
    from app.db.models import Invitation
    from sqlalchemy import select

    _, mail = aws
    login(client)
    parent_id = client.get("/api/session").json()["id"]
    party = body(guests=[{"name": "Guest"}, {"name": "Alex", **email_fields}])
    assert client.put("/api/rsvp", json=party).status_code == 200
    saved = client.get("/api/rsvp").json()["rsvp"]
    assert saved["guests"][1]["name"] == "Alex"
    assert saved["guests"][1].get("email") is None

    async def children():
        async with sessions()() as db:
            return list(
                await db.scalars(
                    select(Invitation).where(Invitation.parent_invitation_id == parent_id)
                )
            )

    assert client.portal.call(children) == []
    recipients = [
        address
        for call in mail.send_email.call_args_list
        for address in call.kwargs["Destination"]["ToAddresses"]
    ]
    recipients.extend(
        address
        for call in mail.send_raw_email.call_args_list
        for address in call.kwargs["Destinations"]
    )
    assert "guest@example.com" in recipients
    assert set(recipients) <= {"guest@example.com", "groom@example.test", "bride@example.test"}


def test_media_admin_preview_uploader_filter_and_bulk_approval(client):
    from app.db.models import Photo
    from sqlalchemy import select

    login(client)
    owner = client.get("/api/session").json()["id"]

    async def seed():
        async with sessions()() as db:
            for number, status in enumerate(["complete", "complete", "pending"]):
                db.add(
                    Photo(
                        id=f"media-{number}",
                        owner=owner,
                        uploader_name="Guest",
                        caption="Memory",
                        content_type="image/jpeg",
                        size=100,
                        status=status,
                        gallery_visible=False,
                        expires=0,
                    )
                )
            await db.commit()

    client.portal.call(seed)
    admin_login(client)
    detail = client.get("/api/admin/photo/details/media-0")
    assert detail.status_code == 200
    assert "Uploaded media preview" in detail.text and "https://example.com/signed" in detail.text
    listing = client.get("/api/admin/photo/list")
    assert "Uploader" in listing.text and "Guest" in listing.text
    assert "Memory" in client.get(f"/api/admin/photo/list?uploader={owner}").text
    assert "Memory" not in client.get("/api/admin/photo/list?uploader=unknown").text
    result = client.get("/api/admin/photo/action/approve-media?pks=media-0,media-1,media-2")
    assert result.status_code == 200

    async def gallery_visible():
        async with sessions()() as db:
            return {row.id: row.gallery_visible for row in (await db.scalars(select(Photo))).all()}

    assert client.portal.call(gallery_visible) == {
        "media-0": True,
        "media-1": True,
        "media-2": False,
    }


@pytest.mark.parametrize("content_type", ["image/jpeg", "video/mp4"])
def test_disguised_non_media_cannot_be_completed(client, aws, content_type):
    storage, _ = aws
    login(client)
    data = b"This is a text file, not an image or video."
    upload = client.post(
        "/api/photos/upload",
        json={
            "filename": "fake.jpg",
            "content_type": content_type,
            "size": len(data),
            "consent": True,
        },
    ).json()
    storage.get_object.return_value = {"ContentLength": len(data), "Body": io.BytesIO(data)}
    assert client.post(f"/api/photos/{upload['id']}/complete").status_code == 422
    storage.put_object.assert_not_called()


def test_seeded_couple_have_personal_gallery_access_without_admin_privileges(client):
    from app.core.security import cipher
    from app.db.models import Invitation
    from app.services.access import ensure_access

    async def credentials(identity):
        async with sessions()() as db:
            invite = await db.get(Invitation, identity)
            assert invite is not None and invite.active and not invite.is_admin
            access = await ensure_access(db, identity)
            await db.commit()
            return (
                invite.name,
                invite.guest.email,
                cipher().decrypt(access.encrypted_code.encode()).decode(),
            )

    for identity, expected_name, expected_email in [
        ("wedding-groom", "Example groom", "groom@example.test"),
        ("wedding-bride", "Example bride", "bride@example.test"),
    ]:
        name, email, code = client.portal.call(credentials, identity)
        assert (name, email) == (expected_name, expected_email)
        login(client, code)
        assert client.get("/api/photos").status_code == 200
        assert client.get("/api/admin/invitations").status_code == 403
        assert (
            client.post(
                "/api/photos/upload",
                json={"filename": "memory.png", "content_type": "image/png", "size": 200},
            ).status_code
            == 200
        )


def test_large_video_uses_owned_multipart_without_consent_requirement(client, aws):
    storage, _ = aws
    login(client)
    size = 6 * 1024**3
    result = client.post(
        "/api/photos/upload",
        json={"filename": "large.mp4", "content_type": "video/mp4", "size": size},
    )
    assert result.status_code == 200
    upload = result.json()
    assert upload["upload"]["multipart"] is True
    assert upload["upload"]["part_size"] >= 64 * 1024**2
    assert client.get(f"/api/photos/{upload['id']}/parts/1").status_code == 200
    assert (
        storage.generate_presigned_url.call_args.kwargs["Params"]["ContentLength"]
        == upload["upload"]["part_size"]
    )
    assert client.get(f"/api/photos/{upload['id']}/parts/10001").status_code == 422
    assert (
        client.post(f"/api/photos/{upload['id']}/complete", json={"parts": []}).status_code == 422
    )
    login(client, "ADMIN-CODE-123")
    assert client.get(f"/api/photos/{upload['id']}/parts/1").status_code == 404


def test_video_longer_than_three_minutes_is_valid(monkeypatch):
    import json
    from types import SimpleNamespace

    from app.services.media import video_preview

    frame = io.BytesIO()
    Image.new("RGB", (32, 24)).save(frame, "PNG")
    probe = {
        "streams": [{"codec_type": "video", "width": 32, "height": 24, "codec_name": "h264"}],
        "format": {"format_name": "mov,mp4", "duration": "7200"},
    }
    calls = iter(
        [
            SimpleNamespace(stdout=json.dumps(probe).encode()),
            SimpleNamespace(stdout=frame.getvalue()),
        ]
    )
    monkeypatch.setattr("app.services.media.subprocess.run", lambda *args, **kwargs: next(calls))
    metadata = {}
    assert video_preview(b"validated through mocked ffprobe", "video/mp4", metadata)
    assert metadata["duration_ms"] == 7200000


def test_calendar_has_no_backend_route(client):
    assert client.get("/api/calendar.ics?locale=en").status_code == 404


def test_authenticated_carousel_only_signs_approved_completed_still_previews(client, aws):
    from app.db.models import Photo

    storage, _ = aws
    assert client.get("/api/photos/random").status_code == 401
    storage.generate_presigned_url.assert_not_called()
    login(client)

    async def seed():
        async with sessions()() as db:
            for i in range(30):
                db.add(
                    Photo(
                        id=f"approved-{i:02}",
                        owner="guest",
                        size=100,
                        content_type="image/jpeg",
                        caption="A happy moment",
                        status="complete",
                        carousel_visible=True,
                        expires=0,
                    )
                )
            for name, status, carousel_visible, content_type in [
                ("pending", "pending", True, "image/jpeg"),
                ("unapproved", "complete", False, "image/jpeg"),
                ("video", "complete", True, "video/mp4"),
                ("not-an-image", "complete", True, "application/pdf"),
            ]:
                db.add(
                    Photo(
                        id=name,
                        owner="guest",
                        size=100,
                        content_type=content_type,
                        caption="Hidden",
                        status=status,
                        carousel_visible=carousel_visible,
                        expires=0,
                    )
                )
            await db.commit()

    client.portal.call(seed)
    response = client.get("/api/photos/carousel")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    items = response.json()["items"]
    assert len(items) == len({item["id"] for item in items}) == 30
    assert all(item["id"].startswith("approved-") for item in items)
    assert all(
        set(item) == {"id", "caption", "preview", "width", "height", "orientation"}
        for item in items
    )
    calls = storage.generate_presigned_url.call_args_list
    assert len(calls) == 30
    assert all(call.args == ("get_object",) for call in calls)
    assert all(call.kwargs["Params"]["Key"].startswith("previews/") for call in calls)
    assert all(call.kwargs["ExpiresIn"] == 3600 for call in calls)
    assert client.get("/api/photos").json()["items"] == []


def test_authenticated_carousel_empty_and_unpublish(client, aws):
    from app.db.models import Photo

    login(client)
    assert client.get("/api/photos/random").json() == {"items": []}

    async def change(carousel_visible):
        async with sessions()() as db:
            photo = await db.get(Photo, "one")
            if photo is None:
                photo = Photo(
                    id="one",
                    owner="guest",
                    size=100,
                    content_type="image/jpeg",
                    caption="One",
                    status="complete",
                    expires=0,
                )
                db.add(photo)
            photo.carousel_visible = carousel_visible
            await db.commit()

    client.portal.call(change, True)
    assert len(client.get("/api/photos/random").json()["items"]) == 1
    client.portal.call(change, False)
    assert client.get("/api/photos/random").json() == {"items": []}


def test_gallery_and_carousel_visibility_are_independent(client, aws):
    from app.db.models import Photo

    login(client)

    async def seed():
        async with sessions()() as db:
            for gallery, carousel in [(False, False), (True, False), (False, True), (True, True)]:
                db.add(
                    Photo(
                        id=f"visibility-{int(gallery)}{int(carousel)}",
                        owner="guest",
                        size=100,
                        content_type="image/jpeg",
                        caption="Moment",
                        status="complete",
                        expires=0,
                        gallery_visible=gallery,
                        carousel_visible=carousel,
                    )
                )
            await db.commit()

    client.portal.call(seed)
    assert {item["id"] for item in client.get("/api/photos").json()["items"]} == {
        "visibility-10",
        "visibility-11",
    }
    assert {item["id"] for item in client.get("/api/photos/random").json()["items"]} == {
        "visibility-01",
        "visibility-11",
    }
    client.delete("/api/session")
    aws[0].generate_presigned_url.reset_mock()
    assert client.get("/api/photos").status_code == 401
    assert client.get("/api/photos/random").status_code == 401
    aws[0].generate_presigned_url.assert_not_called()


def test_admin_edits_gallery_and_carousel_flags_independently(client):
    from app.db.models import Photo

    async def seed():
        async with sessions()() as db:
            db.add(
                Photo(
                    id="moderated-photo",
                    owner="guest",
                    size=100,
                    content_type="image/jpeg",
                    caption="Moment",
                    status="complete",
                    expires=0,
                )
            )
            await db.commit()

    async def flags():
        async with sessions()() as db:
            photo = await db.get(Photo, "moderated-photo")
            assert photo is not None
            return photo.gallery_visible, photo.carousel_visible

    client.portal.call(seed)
    admin_login(client)
    form = client.get("/api/admin/photo/edit/moderated-photo")
    assert "Visible in gallery" in form.text and "Visible in carousel" in form.text
    for gallery, carousel in [(True, False), (False, True), (True, True), (False, False)]:
        data = {"caption": "Moment", "save": "Save"}
        if gallery:
            data["gallery_visible"] = "y"
        if carousel:
            data["carousel_visible"] = "y"
        response = client.post("/api/admin/photo/edit/moderated-photo", data=data)
        assert response.status_code == 200, response.text
        assert client.portal.call(flags) == (gallery, carousel)


@pytest.mark.parametrize(
    "width,height,orientation",
    [(600, 900, "portrait"), (1600, 900, "landscape"), (800, 800, "square"), (0, 0, "unknown")],
)
def test_photo_preview_orientation(client, width, height, orientation):
    from app.db.models import Photo
    from app.services.photos import photo_preview

    preview = photo_preview(Photo(id="orientation", caption="Caption", width=width, height=height))
    assert (preview["width"], preview["height"], preview["orientation"]) == (
        width,
        height,
        orientation,
    )
    assert "original" not in preview


def test_admin_delete_photo_removes_media_and_guest_links(client, aws):
    from app.db.models import Guest, Photo, PhotoGuest
    from sqlalchemy import select

    async def seed():
        async with sessions()() as db:
            db.add(Guest(id="photo-guest", name="Viewer"))
            db.add(
                Photo(
                    id="delete-photo",
                    owner="guest",
                    storage_prefix="guest/",
                    size=100,
                    content_type="image/jpeg",
                    caption="Delete me",
                    status="complete",
                    expires=0,
                    multipart_id="unfinished",
                    motion_multipart_id="unfinished-motion",
                )
            )
            db.add(PhotoGuest(photo_id="delete-photo", guest_id="photo-guest"))
            await db.commit()

    async def remains():
        async with sessions()() as db:
            return await db.get(Photo, "delete-photo"), list(
                await db.scalars(select(PhotoGuest).where(PhotoGuest.photo_id == "delete-photo"))
            )

    client.portal.call(seed)
    client.delete("/api/admin/photo/delete?pks=delete-photo")
    aws[0].delete_object.assert_not_called()
    assert client.portal.call(remains)[0] is not None
    admin_login(client)
    assert (
        'data-bs-target="#modal-delete"' in client.get("/api/admin/photo/details/delete-photo").text
    )
    response = client.delete("/api/admin/photo/delete?pks=delete-photo")
    assert response.status_code == 200
    assert "error=" not in response.text
    assert client.portal.call(remains) == (None, [])
    assert {call.kwargs["Key"] for call in aws[0].delete_object.call_args_list} == {
        "pending/guest/delete-photo",
        "pending/guest/delete-photo-motion",
        "originals/guest/delete-photo",
        "originals/guest/delete-photo-motion",
        "previews/guest/delete-photo.webp",
    }
    assert aws[0].abort_multipart_upload.call_count == 2


def test_admin_delete_keeps_record_when_storage_cleanup_fails(client, aws):
    from app.db.models import Photo

    async def seed():
        async with sessions()() as db:
            db.add(
                Photo(
                    id="failed-delete",
                    owner="guest",
                    size=100,
                    content_type="image/jpeg",
                    caption="Keep record",
                    status="complete",
                    expires=0,
                )
            )
            await db.commit()

    async def remains():
        async with sessions()() as db:
            return await db.get(Photo, "failed-delete") is not None

    client.portal.call(seed)
    admin_login(client)
    aws[0].delete_object.side_effect = RuntimeError("Storage unavailable")
    response = client.delete("/api/admin/photo/delete?pks=failed-delete")
    assert "error=" in response.text
    assert client.portal.call(remains)
