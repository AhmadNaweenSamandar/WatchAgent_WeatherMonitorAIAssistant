import pytest
from src.db.queries import save_reading, get_events
# since we decided to use Test-Driven Development, we will create this engine in Phase 6.
from src.events.engine import evaluate_events 

@pytest.mark.asyncio
async def test_freezing_rain_pivot_trigger(db_connection):
    """
    TDD Test: Asserts that crossing the 0-degree line while precipitating
    correctly triggers a FREEZING_RAIN_PIVOT event.
    """
    # 1. Setup our controlled sequence of readings
    readings = [
        # Hour 1: 2 degrees, raining (No event)
        {"city": "Ottawa", "timestamp": "2026-01-01T10:00", "temperature_2m": 2.0, 
         "apparent_temperature": 0.0, "precipitation": 5.0, "wind_speed_10m": 10.0, "weather_code": 61},
        
        # Hour 2: -1 degree, raining (THIS SHOULD TRIGGER THE EVENT)
        {"city": "Ottawa", "timestamp": "2026-01-01T11:00", "temperature_2m": -1.0, 
         "apparent_temperature": -5.0, "precipitation": 5.0, "wind_speed_10m": 15.0, "weather_code": 61}
    ]

    # Insert readings one by one and run the engine
    for r in readings:
        await save_reading(db_connection, r)
        await evaluate_events(db_connection, r["city"])

    # 2. Assert the expected outcome
    events = await get_events(db_connection, city="Ottawa")
    
    # We expect exactly one event to have fired
    assert len(events) == 1
    assert events[0]["event_type"] == "FREEZING_RAIN_PIVOT"
    assert "crossed the freezing point" in events[0]["reasoning"].lower()