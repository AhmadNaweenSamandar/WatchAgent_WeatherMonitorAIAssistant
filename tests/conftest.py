import os
import pytest
import aiosqlite
import tempfile
from src.db.database import initialize_database

# Force the app to use a temporary database for tests before any other imports
TEST_DB_FD, TEST_DB_PATH = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = TEST_DB_PATH

@pytest.fixture(autouse=True)
async def setup_test_db():
    """Initializes a fresh database schema for every test."""
    await initialize_database()
    yield
    # Cleanup after test
    if os.path.exists(TEST_DB_PATH):
        os.unlink(TEST_DB_PATH)

@pytest.fixture
async def db_connection():
    """Provides an isolated database connection."""
    async with aiosqlite.connect(TEST_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db