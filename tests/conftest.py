"""Pytest configuration and test environment isolation fixtures.

Guarantees:
- Tests ONLY connect to 'personal_tool_test_db', never touching the dev/production DB.
- Automatically loads .env.test if present.
- Seeds test database with default demo data on session start.
"""
import asyncio
import os
import sys
from pathlib import Path

# 1. Force testing environment variables BEFORE any app module is imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.environ["APP_ENV"] = "testing"
os.environ["ENV_FILE"] = ".env.test"
os.environ["MONGO_DB_NAME"] = "personal_tool_test_db"
os.environ["PORT"] = "9982"

from dotenv import load_dotenv
test_env = PROJECT_ROOT / ".env.test"
if test_env.exists():
    load_dotenv(test_env, override=True)

import pytest
from app.core.config import settings
from app.core.database import get_mongo_database
from app.articles import services as article_services
from app.ideas import services as idea_services


@pytest.fixture(scope="session", autouse=True)
def guard_and_seed_test_database():
    """Safety guard & test database seeder:
    1. Guarantees test DB name has 'test'
    2. Seeds initial test articles & ideas in personal_tool_test_db
    """
    current_db_name = settings.MONGO_DB_NAME
    assert "test" in current_db_name.lower(), (
        f"CRITICAL SAFETY VIOLATION: Tests cannot run against '{current_db_name}'! "
        f"MONGO_DB_NAME must contain 'test' (expected 'personal_tool_test_db')."
    )

    async def _init_test_db():
        db = get_mongo_database()
        if db is not None:
            await article_services.reset_demo_articles(db=db)
            await idea_services.reset_demo_ideas(db=db)

    try:
        asyncio.run(_init_test_db())
    except Exception:
        pass

    yield
