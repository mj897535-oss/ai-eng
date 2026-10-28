"""Database engine and session management.

Supports both async (FastAPI application) and sync (Alembic / background scripts).
"""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Async engine for web requests
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG and settings.ENVIRONMENT == "development",
    future=True,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Sync engine for Alembic and testing tools
sync_engine = create_engine(
    settings.DATABASE_URL_SYNC,
    echo=False,
    pool_pre_ping=True,
)

if "sqlite" in settings.DATABASE_URL:
    import os

    def _attach_sqlite_schemas(dbapi_conn: Any, _record: Any) -> None:
        db_dir = "/app" if os.path.exists("/app") else "."
        cursor = dbapi_conn.cursor()
        cursor.execute(f"ATTACH DATABASE '{db_dir}/syntaxlens_identity.db' AS identity")
        cursor.execute(f"ATTACH DATABASE '{db_dir}/syntaxlens_research.db' AS research")
        cursor.close()

    event.listen(sync_engine, "connect", _attach_sqlite_schemas)
    event.listen(async_engine.sync_engine, "connect", _attach_sqlite_schemas)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for injecting async database sessions into FastAPI endpoints."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
