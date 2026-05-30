import asyncio
import logging
from src.core.weather_client import CITIES, fetch_current_weather
from src.db.queries import save_reading
from src.events.engine import evaluate_events

logger = logging.getLogger(__name__)

# 10 minutes in seconds
POLL_INTERVAL_SECONDS = 600 

async def weather_polling_loop(db_connection):
    """
    Continuous background loop that polls Open-Meteo and attempts to save readings.
    Relies on SQLite INSERT OR IGNORE for deduplication.
    """
    logger.info("Starting background weather polling loop...")
    
    while True:
        logger.info("Executing scheduled weather poll for all cities...")
        
        for city, coords in CITIES.items():
            reading_data = await fetch_current_weather(city, coords["lat"], coords["lon"])
            
            if reading_data:
                try:
                    inserted = await save_reading(db_connection, reading_data)
                    if inserted:
                        logger.info(f"New reading stored for {city} at {reading_data['timestamp']}")
                        # NEW LINE: Feed the new reading into the event engine
                        await evaluate_events(db_connection, city)
                    else:
                        logger.debug(f"Duplicate reading ignored for {city} at {reading_data['timestamp']}")
                except Exception as e:
                    logger.error(f"Database error while saving reading for {city}: {e}")
        
        logger.info(f"Poll complete. Sleeping for {POLL_INTERVAL_SECONDS} seconds.")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)