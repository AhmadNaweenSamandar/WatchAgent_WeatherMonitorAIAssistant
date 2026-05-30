from typing import List, Dict, Any, Optional

def check_freezing_rain_pivot(history: List[Dict[str, Any]]) -> Optional[Dict[str, str]]:
    """Event Trigger 1: Evaluates if precipitation is falling while crossing the freezing line."""
    if len(history) < 2:
        return None
        
    curr, prev = history[0], history[1]
    
    if curr["precipitation"] <= 0:
        return None
        
    # Check if temperature crossed 0°C in EITHER direction
    crossed_down = prev["temperature_2m"] > 0 and curr["temperature_2m"] <= 0
    crossed_up = prev["temperature_2m"] < 0 and curr["temperature_2m"] >= 0
    
    if crossed_down or crossed_up:
        return {
            "event_type": "FREEZING_RAIN_PIVOT",
            "description": "Temperature crossed the freezing point during active precipitation.",
            "reasoning": f"Crossed freezing ({prev['temperature_2m']}C -> {curr['temperature_2m']}C) with {curr['precipitation']}mm precip."
        }
    return None


def check_stagnant_heat_dome(history: List[Dict[str, Any]]) -> Optional[Dict[str, str]]:
    """Event Trigger 2: Evaluates if high apparent heat and low wind have persisted for 3 hours."""
    if len(history) < 3:
        return None
    
    # Check if ALL of the last 3 readings meet the criteria
    is_dome = all(
        r["apparent_temperature"] > 32.0 and r["wind_speed_10m"] < 5.0 
        for r in history[:3]
    )
            
    if is_dome:
        return {
            "event_type": "HEAT_DOME_ALERT",
            "description": "Prolonged high heat with stagnant wind detected.",
            "reasoning": "Apparent temperature > 32C and wind speed < 5km/h for 3 consecutive readings."
        }
    return None


def check_apparent_divergence(history: List[Dict[str, Any]]) -> Optional[Dict[str, str]]:
    """Event Trigger 3: evaluates extreme gaps between actual and human-perceived temperatures."""
    if not history:
        return None
        
    curr = history[0]
    delta = abs(curr["temperature_2m"] - curr["apparent_temperature"])
    
    # Delta > 10C combined with high winds (> 30km/h)
    if delta > 10.0 and curr["wind_speed_10m"] > 30.0:
        return {
            "event_type": "APPARENT_DIVERGENCE",
            "description": "Extreme difference between actual and apparent temperature.",
            "reasoning": f"Actual: {curr['temperature_2m']}C, Apparent: {curr['apparent_temperature']}C (Delta: {delta:.1f}C), Wind: {curr['wind_speed_10m']}km/h."
        }
    return None