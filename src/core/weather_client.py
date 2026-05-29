import httpx
import logging
from typing import Dict, Any, Optional
from src.core.config import settings  # Import our type-safe settings

# Configure standard logging
logger = logging.getLogger(__name__)

# Coordinates provided by the requirements
CITIES = {
    "Ottawa": {"lat": 45.42, "lon": -75.69},
    "Toronto": {"lat": 43.70, "lon": -79.42},
    "Vancouver": {"lat": 49.25, "lon": -123.12}
}

async def fetch_current_weather(city: str, lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """
    Fetches the current weather for a specific city using configuration settings.
    Strictly implements resiliency rules to prevent loop crashes.
    """
    # Pull securely from environment variables
    url = settings.OPEN_METEO_BASE_URL
    
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,apparent_temperature,precipitation,wind_speed_10m,weather_code",
        "wind_speed_unit": "kmh",
        "timezone": "auto"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Extract the 'current' block and append the city name for database insertion
            current_data = data.get("current", {})
            current_data["city"] = city
            # Open-Meteo returns 'time', we map it to 'timestamp' for our schema
            current_data["timestamp"] = current_data.pop("time") 
            
            return current_data

    except httpx.HTTPStatusError as e:
        logger.warning(f"Failed to fetch weather for {city}. HTTP Status: {e.response.status_code}. Error: {e}")
    except httpx.RequestError as e:
        logger.warning(f"Network error while fetching weather for {city}. Error: {e}")
    except Exception as e:
        logger.warning(f"Unexpected error fetching weather for {city}. Error: {e}")
        
    return None