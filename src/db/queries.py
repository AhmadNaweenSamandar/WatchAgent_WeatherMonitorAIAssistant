import aiosqlite
from typing import List, Dict, Any, Optional

async def save_reading(db: aiosqlite.Connection, reading_data: Dict[str, Any]) -> bool:
    """
    Persists a weather telemetry record. Utilizes native DB-layer deduplication
    via INSERT OR IGNORE over the composite unique constraint (city, timestamp).
    Returns True if a new row was inserted, False if ignored as a duplicate.
    """
    query = """
        INSERT OR IGNORE INTO readings (
            city, timestamp, temperature_2m, apparent_temperature, 
            precipitation, wind_speed_10m, weather_code
        ) VALUES (:city, :timestamp, :temperature_2m, :apparent_temperature, 
                  :precipitation, :wind_speed_10m, :weather_code);
    """
    cursor = await db.execute(query, reading_data)
    await db.commit()
    return cursor.rowcount > 0

async def save_event(db: aiosqlite.Connection, event_data: Dict[str, Any]) -> None:
    """
    Appends a new notable event record. Append-only execution pattern; 
    no UPDATE or DELETE pathways exist for this dataset.
    """
    query = """
        INSERT INTO events (
            city, timestamp, event_type, description, reasoning
        ) VALUES (:city, :timestamp, :event_type, :description, :reasoning);
    """
    await db.execute(query, event_data)
    await db.commit()

async def get_readings(
    db: aiosqlite.Connection, 
    city: Optional[str] = None, 
    limit: int = 50
) -> List[aiosqlite.Row]:
    """
    Retrieves stored historical telemetry readings sorted by most recent first.
    Optional city parameter provides column-level partitioning filters.
    """
    if city:
        query = "SELECT * FROM readings WHERE city = ? ORDER BY timestamp DESC LIMIT ?;"
        params = (city, limit)
    else:
        query = "SELECT * FROM readings ORDER BY timestamp DESC LIMIT ?;"
        params = (limit,)
        
    async with db.execute(query, params) as cursor:
        return await cursor.fetchall()

async def get_events(
    db: aiosqlite.Connection, 
    city: Optional[str] = None, 
    limit: int = 50
) -> List[aiosqlite.Row]:
    """
    Retrieves detected notable architectural events sorted by execution timeline.
    """
    if city:
        query = "SELECT * FROM events WHERE city = ? ORDER BY timestamp DESC LIMIT ?;"
        params = (city, limit)
    else:
        query = "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?;"
        params = (limit,)
        
    async with db.execute(query, params) as cursor:
        return await cursor.fetchall()

async def get_database_metrics(db: aiosqlite.Connection) -> Dict[str, int]:
    """
    Calculates overall volume summaries for health metrics reporting.
    """
    metrics = {"readings_stored": 0, "events_stored": 0}
    
    async with db.execute("SELECT COUNT(*) FROM readings;") as cursor:
        row = await cursor.fetchone()
        metrics["readings_stored"] = row[0] if row else 0
        
    async with db.execute("SELECT COUNT(*) FROM events;") as cursor:
        row = await cursor.fetchone()
        metrics["events_stored"] = row[0] if row else 0
        
    return metrics