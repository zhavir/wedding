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
    assert "CREATE TABLE guests" in sql
    assert "CREATE TABLE photo_guests" in sql
    assert "DROP TABLE email_copy" in sql
    assert "DROP TABLE rsvp_responses" in sql
    assert "default-it-+1" in sql and "default-en-+1" in sql
    assert "ADD COLUMN guest_id VARCHAR(64)" in sql
    if dsql:
        assert "CREATE UNIQUE INDEX ASYNC uq_invitation_email" in sql
        assert "CREATE UNIQUE INDEX ASYNC uq_invitation_guest" in sql
        assert "sys.wait_for_job" in sql
        added_columns = [line for line in sql.splitlines() if "ADD COLUMN" in line]
        assert all("DEFAULT" not in line and "NOT NULL" not in line for line in added_columns)


def test_guest_migration_rejects_duplicates_before_changing_schema(tmp_path):
    from sqlalchemy import create_engine, inspect, text

    db = create_engine(f"sqlite:///{tmp_path / 'duplicates.db'}")
    config = Config("alembic.ini")
    with db.connect() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "0003_carousel_visibility")
        connection.execute(text("UPDATE invitations SET email='SAME@example.test'"))
        connection.commit()
        with pytest.raises(RuntimeError, match="duplicate groups"):
            command.upgrade(config, "head")
        assert "guests" not in inspect(connection).get_table_names()
        assert "guest_id" not in {c["name"] for c in inspect(connection).get_columns("invitations")}
    db.dispose()


@pytest.mark.parametrize("failure_step", ["index", "drop"])
def test_guest_migration_resumes_after_committed_ddl(tmp_path, monkeypatch, failure_step):
    from alembic.operations import Operations
    from sqlalchemy import create_engine, text

    db = create_engine(f"sqlite:///{tmp_path / 'resume.db'}")
    config = Config("alembic.ini")
    method = "create_index" if failure_step == "index" else "drop_table"
    original = getattr(Operations, method)

    def interrupt(self, name, *args, **kwargs):
        if name == ("uq_invitation_email" if failure_step == "index" else "rsvp_responses"):
            raise RuntimeError("simulated interruption")
        return original(self, name, *args, **kwargs)

    with db.connect() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "0003_carousel_visibility")
        with monkeypatch.context() as patch:
            patch.setattr(Operations, method, interrupt)
            with pytest.raises(RuntimeError, match="simulated interruption"):
                command.upgrade(config, "head")
        connection.rollback()
        command.upgrade(config, "head")
        assert connection.scalar(text("SELECT count(*) FROM guests")) == 2
        assert (
            connection.scalar(text("SELECT count(*) FROM invitations WHERE guest_id IS NULL")) == 0
        )
        assert connection.scalar(text("SELECT count(*) FROM invitation_messages")) == 16
        command.upgrade(config, "head")
    db.dispose()


def test_guest_email_migration_preserves_addresses_and_invitation_ids(tmp_path):
    from sqlalchemy import create_engine, inspect, text

    db = create_engine(f"sqlite:///{tmp_path / 'guest-email.db'}")
    config = Config("alembic.ini")
    with db.connect() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "0004_guests_and_invitations")
        connection.execute(
            text("UPDATE invitations SET email='GROOM@example.test' WHERE id='wedding-groom'")
        )
        connection.execute(text("UPDATE invitations SET email=NULL WHERE id='wedding-bride'"))
        connection.commit()
        before = connection.execute(
            text("SELECT id, guest_id, encrypted_token FROM invitations ORDER BY id")
        ).all()
        connection.commit()
        command.upgrade(config, "head")
        assert "email" not in {c["name"] for c in inspect(connection).get_columns("invitations")}
        assert (
            connection.scalar(text("SELECT email FROM guests WHERE id='wedding-groom'"))
            == "groom@example.test"
        )
        assert connection.scalar(text("SELECT email FROM guests WHERE id='wedding-bride'")) is None
        assert (
            connection.execute(
                text("SELECT id, guest_id, encrypted_token FROM invitations ORDER BY id")
            ).all()
            == before
        )
        command.upgrade(config, "head")
    db.dispose()


@pytest.mark.parametrize(
    "revision",
    [
        "base",
        "0001_initial",
        "0002_email_copy",
        "0003_carousel_visibility",
        "0004_guests_and_invitations",
        "0005_guest_email",
        "0006_guest_language",
        "0007_static_calendar",
    ],
)
def test_every_existing_revision_upgrades_to_current_models(tmp_path, revision):
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from alembic.script import ScriptDirectory
    from app.db.models import Base
    from app.migrations.schema import compare_server_default
    from sqlalchemy import create_engine

    database = create_engine(f"sqlite:///{tmp_path / 'alignment.db'}")
    config = Config("alembic.ini")
    with database.connect() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, revision)
        command.upgrade(config, "head")
        command.upgrade(config, "head")
        context = MigrationContext.configure(
            connection, opts={"compare_server_default": compare_server_default}
        )
        assert context.get_current_heads() == tuple(ScriptDirectory.from_config(config).get_heads())
        assert compare_metadata(context, Base.metadata) == []
    database.dispose()


def test_alignment_preserves_existing_languages_and_custom_plural_messages(tmp_path):
    from sqlalchemy import create_engine, text

    database = create_engine(f"sqlite:///{tmp_path / 'defaults.db'}")
    config = Config("alembic.ini")
    with database.connect() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "0007_static_calendar")
        connection.execute(text("UPDATE guests SET language='en'"))
        connection.execute(text("UPDATE invitation_messages SET plural_text='Custom message'"))
        connection.commit()
        command.upgrade(config, "head")
        assert connection.execute(text("SELECT DISTINCT language FROM guests")).scalars().all() == [
            "en"
        ]
        assert connection.execute(
            text("SELECT DISTINCT plural_text FROM invitation_messages")
        ).scalars().all() == ["Custom message"]
        connection.execute(text("INSERT INTO guests (id, name) VALUES ('new-guest', 'New guest')"))
        assert connection.scalar(text("SELECT language FROM guests WHERE id='new-guest'")) == "it"
    database.dispose()


def test_schema_comparison_detects_default_drift():
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from app.migrations.schema import compare_server_default
    from sqlalchemy import MetaData, String, Table, create_engine

    database = create_engine("sqlite://")
    metadata = MetaData()
    table = Table(
        "example",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("language", String(2), server_default="en"),
    )
    with database.connect() as connection:
        metadata.create_all(connection)
        table.c.language.server_default.arg = "it"  # ty: ignore[invalid-assignment]
        context = MigrationContext.configure(
            connection, opts={"compare_server_default": compare_server_default}
        )
        differences = compare_metadata(context, metadata)
        assert differences and differences[0][0][0] == "modify_default"
    database.dispose()
