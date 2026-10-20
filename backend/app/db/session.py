from collections.abc import AsyncIterator
from functools import lru_cache

from aurora_dsql_psycopg import DSQLAsyncConnection
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.db import dsql as _dsql  # noqa: F401 -- register the async DSQL dialect


def database_url() -> URL:
    cfg = settings()
    if cfg.dsql_host:
        return URL.create(
            "auroradsql+psycopg_async",
            username=cfg.db_user,
            host=cfg.dsql_host,
            database="postgres",
        )
    return make_url(cfg.database_url)


@lru_cache
def engine() -> AsyncEngine:
    cfg = settings()
    host = cfg.dsql_host
    if host:

        async def connect():
            return await DSQLAsyncConnection.connect(
                host=host,
                user=cfg.db_user,
                dbname="postgres",
                region=cfg.aws_region,
                sslmode="verify-full",
                sslrootcert="system",
            )

        return create_async_engine(
            database_url(),
            async_creator=connect,
            pool_pre_ping=True,
            pool_size=2,
            max_overflow=0,
            pool_recycle=600,
        )
    return create_async_engine(database_url(), pool_pre_ping=True)


@lru_cache
def sessions() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine(), expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with sessions()() as db:
        yield db
