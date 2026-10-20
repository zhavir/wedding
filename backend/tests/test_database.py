import asyncio
from io import StringIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from alembic import command
from alembic.config import Config
from app.core.config import settings
from app.db.dsql import AuroraDSQLAsyncDialect
from app.db.session import database_url, engine
from sqlalchemy import Column, Index, Integer, MetaData, Table
from sqlalchemy.engine.reflection import ObjectKind, ObjectScope
from sqlalchemy.schema import CreateIndex


@pytest.fixture(autouse=True)
def database_settings(monkeypatch):
    monkeypatch.setenv("INVITE_ENCRYPTION_KEY", "test")
    monkeypatch.delenv("DSQL_HOST", raising=False)
    settings.cache_clear()
    engine.cache_clear()
    yield
    if engine.cache_info().currsize:
        asyncio.run(engine().dispose())
    engine.cache_clear()
    settings.cache_clear()


@pytest.mark.parametrize("user", ["admin", "wedding_app"])
def test_dsql_engine_uses_iam_connector(monkeypatch, user):
    monkeypatch.setenv("DSQL_HOST", "example.dsql.eu-central-1.on.aws")
    monkeypatch.setenv("DB_USER", user)
    monkeypatch.setenv("AWS_REGION", "eu-central-1")
    connect = AsyncMock(side_effect=RuntimeError("connection reached"))
    monkeypatch.setattr("app.db.session.DSQLAsyncConnection.connect", connect)
    db = engine()
    assert isinstance(db.dialect, AuroraDSQLAsyncDialect)
    assert db.dialect.is_async
    assert not db.dialect.use_native_hstore
    assert db.url.password is None

    async def attempt():
        async with db.connect():
            pass

    with pytest.raises(RuntimeError, match="connection reached"):
        asyncio.run(attempt())
    connect.assert_awaited_once_with(
        host="example.dsql.eu-central-1.on.aws",
        user=user,
        dbname="postgres",
        region="eu-central-1",
        sslmode="verify-full",
        sslrootcert="system",
    )


def test_local_postgres_keeps_asyncpg(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/local")
    assert database_url().drivername == "postgresql+asyncpg"
    assert engine().dialect.name == "postgresql"
    assert engine().dialect.driver == "asyncpg"


def test_dsql_keeps_async_index_compiler():
    table = Table("example", MetaData(), Column("value", Integer))
    sql = str(
        CreateIndex(Index("example_value", table.c.value)).compile(dialect=AuroraDSQLAsyncDialect())
    )
    assert sql.startswith("CREATE INDEX ASYNC ")


def test_dsql_reflection_includes_sqlalchemy_21_collation():
    dialect = AuroraDSQLAsyncDialect()
    dialect.server_version_info = (17, 0)
    query = dialect._columns_query("public", True, ObjectScope.DEFAULT, ObjectKind.TABLE)
    assert "collation" in query.selected_columns
    assert "identity_options" in query.selected_columns
    assert "pg_collation" in str(query.compile(dialect=dialect))


@pytest.mark.parametrize("ddl", [True, False])
@pytest.mark.parametrize("parameters", [True, False])
def test_async_ddl_commits_through_connection_proxy(ddl, parameters):
    cursor = MagicMock(spec=["execute"])
    context = MagicMock(isddl=ddl)
    dialect = AuroraDSQLAsyncDialect()
    if parameters:
        dialect.do_execute(cursor, "statement", {}, context)
        cursor.execute.assert_called_once_with("statement", {})
    else:
        dialect.do_execute_no_params(cursor, "statement", context)
        cursor.execute.assert_called_once_with("statement")
    assert context.root_connection.connection.commit.call_count == int(ddl)


@pytest.mark.parametrize("dsql", [True, False])
def test_offline_migration_uses_configured_dialect(monkeypatch, dsql):
    if dsql:
        monkeypatch.setenv("DSQL_HOST", "example.dsql.eu-central-1.on.aws")
        # Production migrations require host details even when only generating SQL.
        monkeypatch.setenv("WEDDING_GROOM_NAME", "Example groom")
        monkeypatch.setenv("WEDDING_GROOM_EMAIL", "groom@example.test")
        monkeypatch.setenv("WEDDING_BRIDE_NAME", "Example bride")
        monkeypatch.setenv("WEDDING_BRIDE_EMAIL", "bride@example.test")
    output = StringIO()
    config = Config("alembic.ini", output_buffer=output)
    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE alembic_version" in sql
    assert "CREATE TABLE IF NOT EXISTS invitations" in sql
    assert "INSERT INTO alembic_version" in sql
