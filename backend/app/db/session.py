import asyncio
import ssl
from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Protocol, cast

import asyncpg
import boto3
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


class DSQLTokenSigner(Protocol):
    """Boto3 injects these signing helpers at runtime; service stubs omit them."""

    def generate_db_connect_admin_auth_token(self, *, Hostname: str, Region: str) -> str: ...
    def generate_db_connect_auth_token(self, *, Hostname: str, Region: str) -> str: ...


@lru_cache
def engine() -> AsyncEngine:
    cfg = settings()
    host = cfg.dsql_host
    if host is not None:

        async def connect():
            client = cast(DSQLTokenSigner, boto3.client("dsql", region_name=cfg.aws_region))
            signer = (
                client.generate_db_connect_admin_auth_token
                if cfg.db_user == "admin"
                else client.generate_db_connect_auth_token
            )
            password = await asyncio.to_thread(signer, Hostname=host, Region=cfg.aws_region)
            return await asyncpg.connect(
                host=host,
                user=cfg.db_user,
                password=password,
                database="postgres",
                ssl=ssl.create_default_context(),
                statement_cache_size=0,
            )

        return create_async_engine(
            "postgresql+asyncpg://",
            async_creator=connect,
            pool_pre_ping=True,
            pool_size=2,
            max_overflow=0,
            pool_recycle=600,
        )
    return create_async_engine(cfg.database_url, pool_pre_ping=True)


@lru_cache
def sessions() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine(), expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with sessions()() as db:
        yield db
