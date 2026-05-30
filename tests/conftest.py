import os
import tempfile

TEST_DB_FD, TEST_DB_PATH = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = TEST_DB_PATH
os.close(TEST_DB_FD)

import pytest
import aiosqlite
from src.db.database import initialize_database


@pytest.fixture(autouse=True)
async def setup_test_db():
    """Initializes a fresh database schema for every test."""
    await initialize_database()
    yield
    if os.path.exists(TEST_DB_PATH):
        os.unlink(TEST_DB_PATH)


@pytest.fixture
async def db_connection():
    """Provides an isolated database connection."""
    async with aiosqlite.connect(TEST_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db
