import aiosqlite
import logging
from typing import Dict, Any, List
from src.db.queries import save_event
from src.events.triggers import (
    check_freezing_rain_pivot,
    check_stagnant_heat_dome,
    check_apparent_divergence
)

logger = logging.getLogger(__name__)

ACTIVE_TRIGGERS = [
    check_freezing_rain_pivot,
    check_stagnant_heat_dome,
    check_apparent_divergence
]

async def _get_recent_readings(
    db: aiosqlite.Connection, city: str, limit: int = 3
) -> List[Dict[str, Any]]:
    """
    O(1) memory safe query: Only fetches the exact number of readings required.
    Returns them as standard dictionaries.
    """
    query = "SELECT * FROM readings WHERE city = ? ORDER BY timestamp DESC LIMIT ?;"
    async with db.execute(query, (city, limit)) as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def evaluate_events(db_connection: aiosqlite.Connection, city: str) -> None:
    """
    Fetches historical context, executes the Strategy Pattern triggers, 
    and handles state deduplication before saving.
    """
    history = await _get_recent_readings(db_connection, city, limit=3)
    if not history:
        return
        
    curr_timestamp = history[0]["timestamp"]

    for trigger_func in ACTIVE_TRIGGERS:
        event_payload = trigger_func(history)
        
        if event_payload:
            # Deduplication Check: Ensure this event wasn't already fired for this specific timestamp
            query = "SELECT 1 FROM events WHERE city = ? AND timestamp = ? AND event_type = ?"
            async with db_connection.execute(query, (city, curr_timestamp, event_payload["event_type"])) as cursor:
                exists = await cursor.fetchone()
                
            if not exists:
                event_data = {
                    "city": city,
                    "timestamp": curr_timestamp,
                    "event_type": event_payload["event_type"],
                    "description": event_payload["description"],
                    "reasoning": event_payload["reasoning"]
                }
                await save_event(db_connection, event_data)
                logger.info(f"Notable Event Detected: {event_payload['event_type']} in {city}")