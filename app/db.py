from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _connect_args(url: str) -> dict:
    """Managed Postgres requires SSL; local dev doesn't. Enable SSL for non-local hosts
    (lenient verification — fine for an event app behind a managed provider)."""
    is_local = "@localhost" in url or "@127.0.0.1" in url or "@db:" in url
    if is_local:
        return {}
    import ssl

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return {"ssl": ctx}


def get_engine():
    global _engine
    if _engine is None:
        url = get_settings().database_url
        _engine = create_async_engine(url, pool_pre_ping=True, connect_args=_connect_args(url))
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _sessionmaker


async def get_db() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session
