import pytest
from httpx import AsyncClient, ASGITransport
from src.api.main import app
from src.db.queries import save_reading, save_event

@pytest.mark.asyncio
async def test_health_endpoint():
    """
    TDD Test: Validates the /health endpoint contract returns a 200 OK
    and the correct JSON shape. This will pass the test since health endpoint is already implemented.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        response = await ac.get("/health")
        
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "message" in data

@pytest.mark.asyncio
async def test_readings_endpoint(db_connection):
    """
    TDD Test: Validates the /readings endpoint contract filters by city,
    respects limits, and returns the correct list structure.
    """
    # 1. Setup: Insert dummy data into our test database
    dummy_reading = {
        "city": "Ottawa", "timestamp": "2026-05-30T12:00", 
        "temperature_2m": 15.0, "apparent_temperature": 15.0, 
        "precipitation": 0.0, "wind_speed_10m": 10.0, "weather_code": 0
    }
    await save_reading(db_connection, dummy_reading)
    
    # 2. Execute: Hit the API endpoint
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        response = await ac.get("/readings?city=Ottawa&limit=50")
        
    # 3. Assert: Validate the contract
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["city"] == "Ottawa"
    # Ensure database internal IDs aren't leaking if we didn't want them to (or verify structure)
    assert "temperature_2m" in data[0]

@pytest.mark.asyncio
async def test_events_endpoint(db_connection):
    """
    TDD Test: Validates the /events endpoint contract returns formatted anomalies.
    """
    # 1. Setup
    dummy_event = {
        "city": "Ottawa", "timestamp": "2026-05-30T12:00", 
        "event_type": "FREEZING_RAIN_PIVOT", 
        "description": "Test Drop", "reasoning": "Test reasoning"
    }
    await save_event(db_connection, dummy_event)
    
    # 2. Execute
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        response = await ac.get("/events?city=Ottawa&limit=50")
        
    # 3. Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["event_type"] == "FREEZING_RAIN_PIVOT"