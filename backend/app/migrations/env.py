"""Async Alembic environment shared by the CLI and deployment migration command."""

import asyncio

from alembic import context
from alembic.ddl.postgresql import PostgresqlImpl
from app.db.models import Base
from app.db.session import database_url, engine
from sqlalchemy import Connection


class AuroraDSQLImpl(PostgresqlImpl):
    """Register DSQL with Alembic while retaining PostgreSQL schema comparison."""

    __dialect__ = "auroradsql"
    transactional_ddl = False


def migrate(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        transactional_ddl=False,
        transaction_per_migration=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def online() -> None:
    async with engine().connect() as connection:
        await connection.run_sync(migrate)
    await engine().dispose()


if context.is_offline_mode():
    context.configure(
        url=database_url(),
        target_metadata=Base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        transactional_ddl=False,
    )
    with context.begin_transaction():
        context.run_migrations()
elif context.config.attributes.get("connection") is not None:
    migrate(context.config.attributes["connection"])
else:
    asyncio.run(online())
