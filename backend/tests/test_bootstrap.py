import asyncio
from unittest.mock import AsyncMock

import pytest
from app import bootstrap
from app.admin.auth import verify_password
from app.db.models import AdminUser, Base
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
def configured(monkeypatch):
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

    monkeypatch.setattr(bootstrap, "migrate", migrate)
    monkeypatch.setattr(bootstrap, "ensure_admin", admin)
    with TestClient(bootstrap.app) as client:
        assert client.get("/api/health").status_code == 200
        assert not calls
        response = client.post("/bootstrap")
        assert response.json() == {"ok": True, "admin": "created"}
        assert calls == ["migrate", "admin"]


@pytest.mark.parametrize("stage", ["credentials", "migrate", "admin"])
@pytest.mark.parametrize("debug", [False, True])
def test_bootstrap_failure_stops_and_respects_debug_flag(
    monkeypatch, configured, caplog, stage, debug
):
    monkeypatch.setenv("DEBUG_DEPLOY", "1" if debug else "0")
    migration = AsyncMock()
    admin = AsyncMock(return_value="existing")
    monkeypatch.setattr(bootstrap, "migrate", migration)
    monkeypatch.setattr(bootstrap, "ensure_admin", admin)
    if stage == "credentials":
        monkeypatch.setenv("ADMIN_PASSWORD", "short")
    else:
        {"migrate": migration, "admin": admin}[stage].side_effect = RuntimeError(
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
