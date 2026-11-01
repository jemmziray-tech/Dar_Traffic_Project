"""Read Google traffic estimates for immediate display, without storing them."""

import logging
import math
import os
from datetime import datetime, timezone

import googlemaps
import requests
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)
gmaps = None


def initialize_clients():
    """Connect only when executing, so validation can run without cloud secrets."""
    global gmaps
    key = os.getenv("MAPS_API_KEY")
    if not key or key == "YOUR_GOOGLE_API_KEY_HERE":
        raise RuntimeError("MAPS_API_KEY is required for traffic-aware collection")
    gmaps = googlemaps.Client(key=key, timeout=15, retry_timeout=0, retry_over_query_limit=False)


class TrafficObservation(BaseModel):
    """Values returned to the current visitor; these are not a training record."""

    model_config = ConfigDict(allow_inf_nan=False)

    schema_version: int = 2
    source: str = "google_distance_matrix"
    traffic_observed: bool = True
    distance_km: float = Field(..., gt=0)
    road_id: str
    name: str
    normal_mins: float = Field(..., gt=0)
    live_mins: float = Field(..., gt=0)
    delay_mins: float = Field(..., ge=0, description="Delay cannot be negative")
    speed_kmh: float = Field(..., ge=0.0, description="Speed must be a positive float")
    status: str
    weather: str
    precipitation_mm: float | None = Field(None, ge=0.0)


def parse_weather(current):
    """Decode Open-Meteo current weather; missing fields stay unknown.

    Weather codes: https://open-meteo.com/en/docs#weathervariables
    """
    try:
        temperature = float(current["temperature_2m"])
        code = int(current["weather_code"])
        precipitation = float(current["precipitation"])
        if not math.isfinite(temperature) or not math.isfinite(precipitation) or precipitation < 0:
            raise ValueError("Invalid weather values")
    except (KeyError, TypeError, ValueError, OverflowError):
        return "Unknown", None
    if code in (0, 1):
        condition = "Clear"
    elif code in (2, 3):
        condition = "Cloudy"
    elif code in (45, 48):
        condition = "Fog"
    elif code in (51, 53, 55, 56, 57):
        condition = "Drizzle"
    elif code in (61, 63, 65, 66, 67, 80, 81, 82):
        condition = "Rain"
    elif code in (71, 73, 75, 77, 85, 86):
        condition = "Snow"
    elif code in (95, 96, 97, 99):
        condition = "Thunderstorm"
    else:
        return "Unknown", None
    return f"{temperature:g}°C, {condition}", precipitation


def get_weather_for_all_roads(roads):
    """Fetch one location per corridor, without substituting another location."""
    unknown = {road["id"]: ("Unknown", None) for road in roads}
    if not roads:
        return unknown
    try:
        coordinates = [road["start"].split(",") for road in roads]
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": ",".join(lat.strip() for lat, _ in coordinates),
                "longitude": ",".join(lon.strip() for _, lon in coordinates),
                "current": "temperature_2m,precipitation,weather_code",
                "timezone": "Africa/Dar_es_Salaam",
            },
            timeout=15,
        )
        response.raise_for_status()
        locations = response.json()
        if isinstance(locations, dict):
            locations = [locations]
        if len(locations) != len(roads):
            raise ValueError("Weather response location count does not match request")
        if not all(isinstance(location, dict) for location in locations):
            raise TypeError("Invalid weather location response")
        return {
            road["id"]: parse_weather(location.get("current", {}))
            for road, location in zip(roads, locations)
        }
    except (requests.RequestException, ValueError, KeyError, TypeError):
        logger.warning("Weather unavailable; traffic collection will continue", exc_info=True)
        return unknown


def parse_traffic_element(element):
    """Preserve provider durations; never manufacture congestion from time or rain."""
    if element.get("status") != "OK":
        raise ValueError(f"Routing element status: {element.get('status')}")
    normal_seconds = float(element["duration"]["value"])
    live_seconds = float(element["duration_in_traffic"]["value"])
    distance_km = float(element["distance"]["value"]) / 1000
    if not all(
        math.isfinite(value) and value > 0 for value in (normal_seconds, live_seconds, distance_km)
    ):
        raise ValueError("Provider returned non-positive route measurements")
    return {
        "normal_mins": round(normal_seconds / 60, 2),
        "live_mins": round(live_seconds / 60, 2),
        "delay_mins": round(max(0, live_seconds - normal_seconds) / 60, 2),
        "speed_kmh": round(distance_km / (live_seconds / 3600), 2),
        "distance_km": distance_km,
    }


def fetch_road(road, weather_info):
    weather, precip_mm = weather_info
    result = gmaps.distance_matrix(
        origins=road["start"],
        destinations=road["end"],
        mode="driving",
        departure_time="now",
        traffic_model="best_guess",
    )
    if result.get("status") != "OK":
        raise ValueError("Traffic provider did not return a usable route")
    measurements = parse_traffic_element(result["rows"][0]["elements"][0])
    delay = measurements["delay_mins"]
    observation = TrafficObservation(
        road_id=road["id"],
        name=road["name"],
        **measurements,
        status="Smooth" if delay <= 3 else "Moderate" if delay <= 7 else "Heavy Jam",
        weather=weather,
        precipitation_mm=precip_mm,
    ).model_dump()
    observation["timestamp"] = datetime.now(timezone.utc)
    return observation


if __name__ == "__main__":
    raise SystemExit(
        "Scheduled Google history collection is retired. Run live_api.py for live display."
    )
