"""Exercise a disposable PostgreSQL database; never reset the configured app database."""

import asyncio
import os
import uuid
from pathlib import Path

import asyncpg
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from app.core.config import settings
from app.db.models import Base
from app.db.session import engine
from sqlalchemy import text
from sqlalchemy.engine import make_url


async def main():
    url = make_url(settings().database_url)
    if url.get_backend_name() != "postgresql" or settings().dsql_host:
        raise RuntimeError("This destructive migration test only accepts local PostgreSQL.")
    name = "wedding_migration_test_" + uuid.uuid4().hex
    admin = await asyncpg.connect(
        url.set(drivername="postgresql", database="postgres").render_as_string(hide_password=False)
    )
    await admin.execute(f'CREATE DATABASE "{name}"')
    os.environ["DATABASE_URL"] = url.set(database=name).render_as_string(hide_password=False)
    settings.cache_clear()
    engine.cache_clear()
    config = Config()
    import app

    config.set_main_option("script_location", str(Path(app.__file__).parent / "migrations"))

    def cycle(connection):
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
        connection.commit()
        command.downgrade(config, "base")
        command.upgrade(config, "head")
        command.upgrade(config, "head")
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []

    try:
        async with engine().connect() as connection:
            await connection.run_sync(cycle)
            assert await connection.scalar(text("SELECT count(*) FROM invitation_messages")) == 10
            assert (
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM invitations WHERE id IN ('wedding-groom', 'wedding-bride') "
                        "AND active = true AND is_admin = false"
                    )
                )
                == 2
            )
        print("PASS: fresh PostgreSQL upgrade, schema parity, downgrade, re-upgrade and seeds")
    finally:
        await engine().dispose()
        await admin.execute(f'DROP DATABASE "{name}"')
        await admin.close()


asyncio.run(main())
