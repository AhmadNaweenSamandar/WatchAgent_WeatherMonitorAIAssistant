from typing import Optional

import aiosqlite
from fastapi import APIRouter, Depends, Query

from src.db.database import get_db_connection
from src.db.queries import get_database_metrics, get_events, get_readings

router = APIRouter(tags=["Weather Intelligence"])


@router.get("/health")
async def health_check(db: aiosqlite.Connection = Depends(get_db_connection)):
    metrics = await get_database_metrics(db)
    return {
        "status": "ok",
        "readings_stored": metrics["readings_stored"],
        "events_stored": metrics["events_stored"],
    }


@router.get("/readings")
async def fetch_historical_readings(
    city: Optional[str] = None,
    limit: int = Query(50, ge=1),
    db: aiosqlite.Connection = Depends(get_db_connection),
):
    rows = await get_readings(db, city=city, limit=limit)
    return {"readings": [dict(row) for row in rows]}


@router.get("/events")
async def fetch_notable_events(
    city: Optional[str] = None,
    limit: int = Query(50, ge=1),
    db: aiosqlite.Connection = Depends(get_db_connection),
):
    rows = await get_events(db, city=city, limit=limit)
    return {"events": [dict(row) for row in rows]}
