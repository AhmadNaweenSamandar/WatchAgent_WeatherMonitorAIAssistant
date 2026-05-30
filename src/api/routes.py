from fastapi import APIRouter, Depends, Query
from typing import Optional
import aiosqlite
from src.db.database import get_db_connection
from src.db.queries import get_readings, get_events

router = APIRouter(tags=["Weather Intelligence"])

@router.get("/readings")
async def fetch_historical_readings(
    city: Optional[str] = None, 
    limit: int = Query(50, le=100), 
    db: aiosqlite.Connection = Depends(get_db_connection)
):
    """Retrieves raw meteorological telemetry."""
    rows = await get_readings(db, city=city, limit=limit)
    return [dict(row) for row in rows]

@router.get("/events")
async def fetch_notable_events(
    city: Optional[str] = None, 
    limit: int = Query(50, le=100), 
    db: aiosqlite.Connection = Depends(get_db_connection)
):
    """Retrieves detected macro anomalies and meteorological events."""
    rows = await get_events(db, city=city, limit=limit)
    return [dict(row) for row in rows]