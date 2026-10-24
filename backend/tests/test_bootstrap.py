import asyncio
from unittest.mock import AsyncMock, MagicMock

import boto3
import pytest
from app import bootstrap
from app.admin.auth import verify_password
from app.db.models import AdminUser, Base
from botocore.stub import Stubber
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def test_bootstrap_admin_preserves_existing_account_and_leaves_mfa_for_login(tmp_path, monkeypatch):
    async def scenario():
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/admin.db")
        factory = async_sessionmaker(engine, expire_on_commit=False)
        monkeypatch.setattr(bootstrap, "sessions", lambda: factory)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        try:
            assert await bootstrap.ensure_admin("admin", "initial-password-123") == "created"
            async with factory() as db:
                user = await db.get(AdminUser, "admin")
                assert user is not None
                assert verify_password("initial-password-123", user.password_hash)
                assert not user.totp_enabled
                assert user.totp_secret == ""
                user.totp_enabled = True
                user.totp_secret = "encrypted-enrollment"
                user.totp_last_step = 123
                user.failed_attempts = 5
                user.locked_until = 456
                user.active = False
                await db.commit()
                before = {
                    column.name: getattr(user, column.name)
                    for column in AdminUser.__table__.columns
                }
            assert await bootstrap.ensure_admin("admin", "different-password-456") == "existing"
            async with factory() as db:
                user = await db.get(AdminUser, "admin")
                assert user is not None
                assert {
                    column.name: getattr(user, column.name)
                    for column in AdminUser.__table__.columns
                } == before
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.fixture
def ses(monkeypatch, configured):
    client = boto3.client(
        "sesv2", region_name="eu-central-1", aws_access_key_id="test", aws_secret_access_key="test"
    )
    monkeypatch.setattr(bootstrap.boto3, "client", lambda *args, **kwargs: client)
    monkeypatch.setenv("SES_IDENTITY", "example.com")
    monkeypatch.setenv("SITE_URL", "https://example.com")
    monkeypatch.setenv("WEDDING_GROOM_EMAIL", "groom@example.com")
    with Stubber(client) as stub:
        yield stub
        stub.assert_no_pending_responses()


@pytest.mark.parametrize(
    "review,expected", [("PENDING", "pending"), ("DENIED", "denied"), ("GRANTED", "review-granted")]
)
def test_existing_ses_review_is_not_resubmitted(ses, review, expected):
    ses.add_response(
        "get_account",
        {"ProductionAccessEnabled": False, "Details": {"ReviewDetails": {"Status": review}}},
        {},
    )
    assert bootstrap.request_ses_access(bootstrap.BootstrapSettings()) == expected


def test_ses_approved(ses):
    ses.add_response("get_account", {"ProductionAccessEnabled": True}, {})
    assert bootstrap.request_ses_access(bootstrap.BootstrapSettings()) == "approved"


def test_ses_waits_for_identity_verification(ses):
    ses.add_response("get_account", {}, {})
    ses.add_response(
        "get_email_identity", {"VerifiedForSendingStatus": False}, {"EmailIdentity": "example.com"}
    )
    assert bootstrap.request_ses_access(bootstrap.BootstrapSettings()) == "identity-unverified"


@pytest.mark.parametrize("review", [None, "FAILED"])
@pytest.mark.parametrize("conflict", [False, True])
def test_ses_submission_and_concurrent_request(ses, review, conflict):
    ses.add_response(
        "get_account", {"Details": {"ReviewDetails": {"Status": review}}} if review else {}, {}
    )
    ses.add_response(
        "get_email_identity", {"VerifiedForSendingStatus": True}, {"EmailIdentity": "example.com"}
    )
    expected = dict(
        ProductionAccessEnabled=True,
        MailType="TRANSACTIONAL",
        WebsiteURL="https://example.com",
        AdditionalContactEmailAddresses=["groom@example.com"],
        ContactLanguage="EN",
    )
    if conflict:
        ses.add_client_error(
            "put_account_details", service_error_code="ConflictException", expected_params=expected
        )
    else:
        ses.add_response("put_account_details", {}, expected)
    assert bootstrap.request_ses_access(bootstrap.BootstrapSettings()) == (
        "pending" if conflict else "submitted"
    )


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv("SES_IDENTITY", "example.com")
    monkeypatch.setenv("SITE_URL", "https://example.com")
    monkeypatch.setenv("WEDDING_GROOM_EMAIL", "groom@example.com")
    monkeypatch.setenv("ADMIN_USERNAME", "Wedding.Admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "a-secure-initial-password")
    monkeypatch.setenv("RUNTIME_ROLE_ARN", "arn:aws:iam::123456789012:role/runtime")


def test_bootstrap_order_and_readiness(monkeypatch, configured):
    calls = []

    async def migrate(role):
        calls.append("migrate")

    async def admin(username, password):
        assert username == "wedding.admin"
        calls.append("admin")
        return "created"

    def ses(config):
        calls.append("ses")
        return "submitted"

    monkeypatch.setattr(bootstrap, "migrate", migrate)
    monkeypatch.setattr(bootstrap, "ensure_admin", admin)
    monkeypatch.setattr(bootstrap, "request_ses_access", ses)
    with TestClient(bootstrap.app) as client:
        assert client.get("/api/health").status_code == 200
        assert not calls
        response = client.post("/bootstrap")
        assert response.json() == {"ok": True, "admin": "created", "ses": "submitted"}
        assert calls == ["migrate", "admin", "ses"]


@pytest.mark.parametrize("stage", ["credentials", "migrate", "admin", "ses"])
@pytest.mark.parametrize("debug", [False, True])
def test_bootstrap_failure_stops_and_respects_debug_flag(
    monkeypatch, configured, caplog, stage, debug
):
    monkeypatch.setenv("DEBUG_DEPLOY", "1" if debug else "0")
    migration = AsyncMock()
    admin = AsyncMock(return_value="existing")
    ses = MagicMock(return_value="approved")
    monkeypatch.setattr(bootstrap, "migrate", migration)
    monkeypatch.setattr(bootstrap, "ensure_admin", admin)
    monkeypatch.setattr(bootstrap, "request_ses_access", ses)
    if stage == "credentials":
        monkeypatch.setenv("ADMIN_PASSWORD", "short")
    else:
        {"migrate": migration, "admin": admin, "ses": ses}[stage].side_effect = RuntimeError(
            "private-sensitive-data"
        )
    with TestClient(bootstrap.app) as client:
        response = client.post("/bootstrap")
    assert response.status_code == 500
    if debug:
        assert response.json()["ok"] is False
        assert response.json()["phase"] == {"migrate": "migrations", "admin": "administrator"}.get(
            stage, stage
        )
        assert "error" in response.json()
        assert "Traceback" in caplog.text
        if stage != "credentials":
            assert "private-sensitive-data" in response.json()["error"]
    else:
        assert response.json() == {"ok": False}
        assert "private-sensitive-data" not in response.text + caplog.text
    if stage in {"credentials", "migrate"}:
        admin.assert_not_called()
    if stage != "ses":
        ses.assert_not_called()
