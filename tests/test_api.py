import pytest
from httpx import AsyncClient, ASGITransport
from src.api.main import app
from src.db.queries import save_reading, save_event

READING_FIELDS = {
    "id", "city", "timestamp", "temperature_2m", "apparent_temperature",
    "precipitation", "wind_speed_10m", "weather_code", "created_at",
}
EVENT_FIELDS = {
    "id", "city", "timestamp", "event_type", "description", "reasoning", "created_at",
}


@pytest.mark.asyncio
async def test_health_endpoint(db_connection):
    """GET /health → 200 { status, readings_stored, events_stored }"""
    await save_reading(
        db_connection,
        {
            "city": "Ottawa",
            "timestamp": "2026-05-30T12:00",
            "temperature_2m": 15.0,
            "apparent_temperature": 15.0,
            "precipitation": 0.0,
            "wind_speed_10m": 10.0,
            "weather_code": 0,
        },
    )
    await save_event(
        db_connection,
        {
            "city": "Ottawa",
            "timestamp": "2026-05-30T12:00",
            "event_type": "FREEZING_RAIN_PIVOT",
            "description": "Test Drop",
            "reasoning": "Test reasoning",
        },
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        response = await ac.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok", "readings_stored": 1, "events_stored": 1}


@pytest.mark.asyncio
async def test_health_endpoint_empty_database():
    """GET /health returns zero counts when database is empty."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        response = await ac.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "readings_stored": 0, "events_stored": 0}


@pytest.mark.asyncio
async def test_readings_endpoint(db_connection):
    """GET /readings?city=Ottawa&limit=50 → 200 { readings: [...] }"""
    dummy_reading = {
        "city": "Ottawa",
        "timestamp": "2026-05-30T12:00",
        "temperature_2m": 15.0,
        "apparent_temperature": 15.0,
        "precipitation": 0.0,
        "wind_speed_10m": 10.0,
        "weather_code": 0,
    }
    await save_reading(db_connection, dummy_reading)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        response = await ac.get("/readings?city=Ottawa&limit=50")

    assert response.status_code == 200
    data = response.json()
    assert list(data.keys()) == ["readings"]
    assert isinstance(data["readings"], list)
    assert len(data["readings"]) == 1
    assert set(data["readings"][0].keys()) == READING_FIELDS
    assert data["readings"][0]["city"] == "Ottawa"


@pytest.mark.asyncio
async def test_readings_endpoint_empty_list(db_connection):
    """GET /readings returns an empty readings array when no data exists."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        response = await ac.get("/readings?city=Ottawa&limit=50")

    assert response.status_code == 200
    assert response.json() == {"readings": []}


@pytest.mark.asyncio
async def test_events_endpoint(db_connection):
    """GET /events?city=Ottawa&limit=50 → 200 { events: [...] }"""
    dummy_event = {
        "city": "Ottawa",
        "timestamp": "2026-05-30T12:00",
        "event_type": "FREEZING_RAIN_PIVOT",
        "description": "Test Drop",
        "reasoning": "Test reasoning",
    }
    await save_event(db_connection, dummy_event)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        response = await ac.get("/events?city=Ottawa&limit=50")

    assert response.status_code == 200
    data = response.json()
    assert list(data.keys()) == ["events"]
    assert isinstance(data["events"], list)
    assert len(data["events"]) == 1
    assert set(data["events"][0].keys()) == EVENT_FIELDS
    assert data["events"][0]["event_type"] == "FREEZING_RAIN_PIVOT"


@pytest.mark.asyncio
async def test_events_endpoint_empty_list(db_connection):
    """GET /events returns an empty events array when no events exist."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        response = await ac.get("/events?city=Ottawa&limit=50")

    assert response.status_code == 200
    assert response.json() == {"events": []}
