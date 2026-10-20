import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest
from app.manage import migrate
from sqlalchemy.exc import NotSupportedError


@pytest.mark.parametrize("role_exists", [False, True])
@pytest.mark.parametrize("fail_commit", [False, True])
def test_runtime_role_grants(monkeypatch, role_exists, fail_commit):
    statements = []
    connection = AsyncMock()
    connection.scalar.return_value = 1 if role_exists else None

    async def execute(statement):
        sql = str(statement)
        assert "ON SCHEMA public" not in sql
        statements.append(sql)

    connection.execute.side_effect = execute

    class Engine:
        @asynccontextmanager
        async def connect(self):
            yield connection

        @asynccontextmanager
        async def begin(self):
            yield connection
            if fail_commit and statements and statements[-1].startswith("GRANT"):
                raise NotSupportedError(None, None, RuntimeError("commit rejected"))

    monkeypatch.setattr("app.manage.engine", lambda: Engine())
    role = "arn:aws:iam::123456789012:role/wedding-runtime"
    if fail_commit:
        with pytest.raises(NotSupportedError) as caught:
            asyncio.run(migrate(role))
        assert caught.value.__notes__ == [
            f"Runtime-role permission setup failed for: {statements[-1]}"
        ]
        return

    asyncio.run(migrate(role))
    connection.run_sync.assert_awaited_once()
    assert ("CREATE ROLE wedding_app WITH LOGIN" in statements) is not role_exists
    grants = [sql for sql in statements if sql.startswith("GRANT")]
    assert len(grants) == 3
    assert grants[0].startswith("GRANT SELECT, INSERT, UPDATE ON TABLE ")
    assert '"admin_users"' not in grants[0]
    assert grants[1] == (
        "GRANT SELECT, UPDATE (failed_attempts, locked_until, totp_secret, "
        "totp_enabled, totp_last_step, version) ON admin_users TO wedding_app"
    )
    assert grants[2] == "GRANT DELETE ON invitation_messages TO wedding_app"
    assert statements[-1] == f"AWS IAM GRANT wedding_app TO '{role}'"


@pytest.mark.parametrize(
    "missing",
    ["WEDDING_GROOM_NAME", "WEDDING_GROOM_EMAIL", "WEDDING_BRIDE_NAME", "WEDDING_BRIDE_EMAIL"],
)
def test_initial_production_migration_requires_host_configuration(monkeypatch, missing):
    from importlib import import_module

    migration = import_module("app.migrations.versions.0001_initial")
    monkeypatch.setenv("DSQL_HOST", "example.dsql.test")
    for key in (
        "WEDDING_GROOM_NAME",
        "WEDDING_GROOM_EMAIL",
        "WEDDING_BRIDE_NAME",
        "WEDDING_BRIDE_EMAIL",
    ):
        monkeypatch.setenv(key, "configured")
    monkeypatch.delenv(missing)
    # No Alembic context exists: validation must fail before any schema operation.
    with pytest.raises(ValueError, match=missing):
        migration.upgrade()
