import pytest
import respx
import httpx
from src.core.weather_client import fetch_current_weather
from src.db.queries import save_reading

@pytest.mark.asyncio
@respx.mock
async def test_api_mock_and_deduplication(db_connection):
    """
    Validates that the Open-Meteo API is successfully mocked, 
    and that duplicate readings are rejected by the database layer.
    """
    # 1. Mock the Open-Meteo endpoint
    mock_url = "https://api.open-meteo.com/v1/forecast"
    mock_response = {
        "current": {
            "time": "2026-05-29T12:00",
            "temperature_2m": 15.0,
            "apparent_temperature": 14.5,
            "precipitation": 0.0,
            "wind_speed_10m": 10.0,
            "weather_code": 0
        }
    }
    
    respx.get(mock_url).respond(status_code=200, json=mock_response)
    
    # 2. Fetch the mocked data
    reading = await fetch_current_weather("Ottawa", 45.42, -75.69)
    assert reading is not None
    assert reading["city"] == "Ottawa"
    assert reading["timestamp"] == "2026-05-29T12:00"

    # 3. Test Deduplication
    # First insert should succeed
    inserted_first = await save_reading(db_connection, reading)
    assert inserted_first is True
    
    # Second insert with the exact same data should be ignored
    inserted_second = await save_reading(db_connection, reading)
    assert inserted_second is False

    # Verify only ONE row exists in the database
    async with db_connection.execute("SELECT COUNT(*) FROM readings") as cursor:
        count = await cursor.fetchone()
        assert count[0] == 1