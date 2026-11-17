# ruff: noqa: F811
"""Authentication limits must survive new sessions and cover password and OTP guesses."""

import re
import time

import pyotp
import pytest
from app.admin.auth import hash_password
from app.core.security import cipher
from app.db.models import AdminUser
from app.db.session import sessions
from test_api import aws, client, invitation_code  # noqa: F401

PASSWORD = "testing-password-long"
SECRET = "JBSWY3DPEHPK3PXP"


@pytest.fixture
def clock(monkeypatch):
    now = [int(time.time()) // 60 * 60 + 1]
    monkeypatch.setattr("app.services.access.time.time", lambda: now[0])
    return now


def seed_admin(client, *, enrolled=True):
    async def seed():
        async with sessions()() as db:
            db.add(
                AdminUser(
                    username="organiser",
                    password_hash=hash_password(PASSWORD),
                    version="test-version",
                    totp_secret=cipher().encrypt(SECRET.encode()).decode(),
                    totp_enabled=enrolled,
                    active=True,
                )
            )
            await db.commit()

    client.portal.call(seed)


@pytest.mark.parametrize("use_code", [False, True])
def test_invitation_attempts_block_valid_credentials_until_window_expires(client, clock, use_code):
    credential = invitation_code(client) if use_code else "GUEST-CODE-123"
    for attempt in range(10):
        # Caller-controlled headers and clearing cookies must not reset the counter.
        client.cookies.clear()
        assert (
            client.post(
                "/api/session",
                json={"code": f"wrong-code-{attempt}"},
                headers={"X-Forwarded-For": f"192.0.2.{attempt}"},
            ).status_code
            == 401
        )
    response = client.post("/api/session", json={"code": credential})
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "59"
    assert client.get("/api/session").status_code == 401
    # Reading the gate and the independent recovery budget remain available.
    assert (
        client.post("/api/session/recover", json={"email": "missing@example.com"}).status_code
        == 202
    )
    clock[0] += 60
    assert client.post("/api/session", json={"code": credential}).status_code == 200


def test_unknown_admin_usernames_share_a_limit_before_password_hashing(client, clock, monkeypatch):
    checks = []

    def reject(*args):
        checks.append(args)
        return False

    monkeypatch.setattr("app.admin.auth.verify_password", reject)
    for attempt in range(10):
        client.cookies.clear()
        assert (
            client.post(
                "/api/admin/login",
                data={"username": f"unknown-{attempt}", "password": "wrong"},
            ).status_code
            == 400
        )
    response = client.post("/api/admin/login", data={"username": "another", "password": "wrong"})
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "59"
    assert len(checks) == 10
    assert client.get("/api/admin/login").status_code == 200
    clock[0] += 60
    assert client.post("/api/admin/login", data={}).status_code == 400
    assert len(checks) == 11


@pytest.mark.parametrize("wrong_password", [True, False])
def test_admin_password_and_otp_failures_lock_account_for_fifteen_minutes(
    client, clock, monkeypatch, wrong_password
):
    seed_admin(client)
    for _ in range(5):
        assert (
            client.post(
                "/api/admin/login",
                data={"username": "organiser", "password": "wrong" if wrong_password else PASSWORD},
            ).status_code
            == 400
        )

    async def locked_until():
        async with sessions()() as db:
            user = await db.get(AdminUser, "organiser")
            assert user is not None
            return user.locked_until

    assert client.portal.call(locked_until) == clock[0] + 900
    # An expired IP budget must not bypass the longer account lock.
    clock[0] += 60
    with monkeypatch.context() as patch:

        def unexpected_hash(*args):
            pytest.fail("Locked accounts must be rejected before password hashing")

        patch.setattr("app.admin.auth.verify_password", unexpected_hash)
        assert (
            client.post(
                "/api/admin/login", data={"username": "organiser", "password": PASSWORD}
            ).status_code
            == 400
        )
    clock[0] += 840
    assert (
        client.post(
            "/api/admin/login",
            data={
                "username": "organiser",
                "password": PASSWORD,
                "otp": pyotp.TOTP(SECRET).at(clock[0]),
            },
            follow_redirects=False,
        ).status_code
        == 302
    )


def test_mfa_enrollment_and_admin_login_share_client_budget(client, clock):
    seed_admin(client, enrolled=False)
    response = client.post("/api/admin/login", data={"username": "organiser", "password": PASSWORD})
    assert "Set up two-factor authentication" in response.text
    for _ in range(9):
        assert client.post("/api/admin/mfa", data={"csrf": "wrong"}).status_code == 403
    response = client.post("/api/admin/mfa", data={"csrf": "wrong"})
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "59"
    assert client.post("/api/admin/login", data={}).status_code == 429


def test_mfa_enrollment_invalid_codes_also_lock_account(client, clock):
    seed_admin(client, enrolled=False)
    response = client.post("/api/admin/login", data={"username": "organiser", "password": PASSWORD})
    match = re.search(r'name="csrf" value="([^"]+)"', response.text)
    assert match is not None
    csrf = match.group(1)
    for _ in range(5):
        response = client.post("/api/admin/mfa", data={"csrf": csrf, "otp": "invalid"})
        assert "Invalid or expired code" in response.text
    assert (
        client.post(
            "/api/admin/mfa",
            data={"csrf": csrf, "otp": pyotp.TOTP(SECRET).at(clock[0])},
            follow_redirects=False,
        ).status_code
        == 303
    )
    assert client.get("/api/admin/invitation/list", follow_redirects=False).status_code == 302
