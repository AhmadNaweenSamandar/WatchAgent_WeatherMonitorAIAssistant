import pytest
from src.db.queries import save_reading, get_events
from src.events.engine import evaluate_events

@pytest.mark.asyncio
async def test_freezing_rain_pivot_trigger(db_connection):
    """
    TDD Test for Event Trigger 1: Asserts that crossing the 0-degree line while precipitating
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



@pytest.mark.asyncio
async def test_stagnant_heat_dome_trigger(db_connection):
    """
    TDD Test for Event Trigger 2: Asserts that 3 consecutive hours of apparent temperature > 32C
    with wind speed < 5km/h triggers a HEAT_DOME_ALERT.
    """
    # Setup: 3 consecutive hours of hot, still air
    readings = [
        {"city": "Toronto", "timestamp": "2026-07-15T12:00", "temperature_2m": 30.0, 
         "apparent_temperature": 33.0, "precipitation": 0.0, "wind_speed_10m": 3.0, "weather_code": 0},
        {"city": "Toronto", "timestamp": "2026-07-15T13:00", "temperature_2m": 31.0, 
         "apparent_temperature": 34.0, "precipitation": 0.0, "wind_speed_10m": 2.0, "weather_code": 0},
        {"city": "Toronto", "timestamp": "2026-07-15T14:00", "temperature_2m": 31.5, 
         "apparent_temperature": 34.5, "precipitation": 0.0, "wind_speed_10m": 4.0, "weather_code": 0}
    ]

    for r in readings:
        await save_reading(db_connection, r)
        await evaluate_events(db_connection, r["city"])

    events = await get_events(db_connection, city="Toronto")
    
    # It should only fire ONCE after the 3rd consecutive reading is processed
    assert len(events) == 1
    assert events[0]["event_type"] == "HEAT_DOME_ALERT"



@pytest.mark.asyncio
async def test_apparent_divergence_trigger(db_connection):
    """
    TDD Test for Event Trigger 3: Asserts that a delta > 10C between actual and apparent temperature combined with high wind speed
    like 45km/h triggers an APPARENT_DIVERGENCE event.
    """
    # Setup: -5C actual, but severe wind makes it feel like -16C (11 degree delta)
    reading = {
        "city": "Vancouver", "timestamp": "2026-02-10T08:00", "temperature_2m": -5.0, 
        "apparent_temperature": -16.0, "precipitation": 0.0, "wind_speed_10m": 45.0, "weather_code": 3
    }

    await save_reading(db_connection, reading)
    await evaluate_events(db_connection, reading["city"])

    events = await get_events(db_connection, city="Vancouver")
    
    assert len(events) == 1
    assert events[0]["event_type"] == "APPARENT_DIVERGENCE"
    assert "extreme difference" in events[0]["reasoning"].lower()