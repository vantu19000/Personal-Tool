"""Database connection setup using MongoDB (Motor async driver).

Provides async client, database access dependency, and health check utility.
Includes graceful fallback if MongoDB or motor is not yet available.
"""
from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Try importing Motor async MongoDB driver safely
try:
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
    HAS_MOTOR = True
except ImportError:
    HAS_MOTOR = False
    AsyncIOMotorClient = None
    AsyncIOMotorDatabase = None
    logger.warning("Package 'motor' is not installed. Run: pip install motor pymongo")


_client: Optional[Any] = None
_db: Optional[Any] = None


def get_mongo_client() -> Optional[Any]:
    """Get or initialize singleton AsyncIOMotorClient."""
    global _client
    if not HAS_MOTOR:
        return None
    if _client is None:
        try:
            _client = AsyncIOMotorClient(
                settings.mongodb_uri,
                serverSelectionTimeoutMS=2500,
                connectTimeoutMS=2500,
            )
        except Exception as exc:
            logger.warning(f"Failed to initialize Mongo client: {exc}")
            _client = None
    return _client


def get_mongo_database() -> Optional[Any]:
    """Get the default MongoDB database instance."""
    global _db
    if _db is None:
        client = get_mongo_client()
        if client:
            _db = client[settings.MONGO_DB_NAME]
    return _db


async def get_db() -> AsyncGenerator[Optional[Any], None]:
    """FastAPI dependency for obtaining the async MongoDB database.

    Usage in routes:
        @router.get("/items")
        async def list_items(db = Depends(get_db)):
            if db is not None:
                items = await db["collection"].find().to_list(100)
    """
    database = get_mongo_database()
    yield database


async def check_db_connection() -> dict:
    """Kiểm tra trạng thái kết nối tới MongoDB database (Docker/Local).

    Returns:
        dict: {"status": "ok" | "error", "connected": bool, ...}
    """
    if not HAS_MOTOR:
        return {
            "status": "error",
            "connected": False,
            "database": settings.MONGO_DB_NAME,
            "host": settings.MONGO_HOST,
            "port": settings.MONGO_PORT,
            "engine": "MongoDB",
            "error": "Thư viện 'motor' chưa được cài đặt. Chạy: pip install motor pymongo",
        }

    try:
        client = get_mongo_client()
        if not client:
            raise ConnectionError("Không thể tạo MongoDB client.")

        # Ping admin database
        ping_result = await client.admin.command("ping")
        return {
            "status": "ok",
            "connected": True,
            "database": settings.MONGO_DB_NAME,
            "host": settings.MONGO_HOST,
            "port": settings.MONGO_PORT,
            "engine": "MongoDB",
            "ping": ping_result,
        }
    except Exception as exc:
        logger.warning(f"MongoDB connection check failed: {exc}")
        return {
            "status": "error",
            "connected": False,
            "database": settings.MONGO_DB_NAME,
            "host": settings.MONGO_HOST,
            "port": settings.MONGO_PORT,
            "engine": "MongoDB",
            "error": str(exc),
        }


# Re-export BaseMongoRepository for convenience across modules
try:
    from app.core.mongo_base import BaseMongoRepository
except ImportError:
    pass

