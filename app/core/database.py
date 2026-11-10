"""Database connection setup using SQLAlchemy 2.0.

Provides both Async (recommended for FastAPI) and Sync sessions,
declarative Base model, and connection health check utility.
"""
from __future__ import annotations

import logging
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Declarative Base
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


# ---------------------------------------------------------------------------
# Async Engine & Session (Primary for FastAPI endpoints)
# ---------------------------------------------------------------------------
async_engine = create_async_engine(
    settings.async_database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for obtaining an asynchronous database session.

    Usage in routes:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Sync Engine & Session (Useful for background workers, one-off scripts, migrations)
# ---------------------------------------------------------------------------
sync_engine = create_engine(
    settings.sync_database_url,
    echo=False,
    pool_pre_ping=True,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)


def get_sync_db() -> Generator[Session, None, None]:
    """Dependency / context helper for synchronous database session."""
    db = SyncSessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
async def check_db_connection() -> dict:
    """Kiểm tra trạng thái kết nối tới PostgreSQL database.

    Returns:
        dict: {"status": "ok" | "error", "message": str, ...}
    """
    try:
        async with async_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            val = result.scalar()
            return {
                "status": "ok",
                "connected": True,
                "database": settings.DB_NAME,
                "host": settings.DB_HOST,
                "port": settings.DB_PORT,
                "user": settings.DB_USER,
                "query_test": val,
            }
    except Exception as exc:
        logger.warning(f"Database connection check failed: {exc}")
        return {
            "status": "error",
            "connected": False,
            "database": settings.DB_NAME,
            "host": settings.DB_HOST,
            "port": settings.DB_PORT,
            "user": settings.DB_USER,
            "error": str(exc),
        }


async def init_db() -> None:
    """Tạo bảng tự động cho tất cả các model kế thừa từ Base (nếu bảng chưa tồn tại)."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
