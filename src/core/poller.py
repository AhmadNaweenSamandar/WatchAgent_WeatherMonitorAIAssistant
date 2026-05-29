import asyncio
import logging
from src.core.weather_client import CITIES, fetch_current_weather
from src.db.queries import save_reading

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
                    # Attempt to save. The database enforces UNIQUE(city, timestamp)
                    inserted = await save_reading(db_connection, reading_data)
                    if inserted:
                        logger.info(f"New reading stored for {city} at {reading_data['timestamp']}")
                    else:
                        logger.debug(f"Duplicate reading ignored for {city} at {reading_data['timestamp']}")
                except Exception as e:
                    logger.error(f"Database error while saving reading for {city}: {e}")
        
        logger.info(f"Poll complete. Sleeping for {POLL_INTERVAL_SECONDS} seconds.")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)