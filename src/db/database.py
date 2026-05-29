import os
import aiosqlite
from typing import AsyncGenerator

# Resolve database path from environment or default to local storage
DATABASE_PATH = os.getenv("DATABASE_URL", "data/weather.db")

async def get_db_connection() -> AsyncGenerator[aiosqlite.Connection, None]:
    """
    Asynchronous context provider for SQLite database connections.
    Enforces Write-Ahead Logging (WAL) and foreign key constraints per connection.
    """
    # Ensure data directory exists
    dir_name = os.path.dirname(DATABASE_PATH)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
        
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Enable WAL mode for concurrent read/write performance
        await db.execute("PRAGMA journal_mode=WAL;")
        # Enforce relational integrity constraints
        await db.execute("PRAGMA foreign_keys = ON;")
        yield db

async def initialize_database() -> None:
    """
    Executes structural schema creation. Safe to run on every application startup
    due to conditional IF NOT EXISTS declarations.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Create readings table with a composite unique constraint for deduplication
        await db.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                temperature_2m REAL NOT NULL,
                apparent_temperature REAL NOT NULL,
                precipitation REAL NOT NULL,
                wind_speed_10m REAL NOT NULL,
                weather_code INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(city, timestamp)
            );
        """)
        
        # Create immutable events log table linked back to readings
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                description TEXT NOT NULL,
                reasoning TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.commit()