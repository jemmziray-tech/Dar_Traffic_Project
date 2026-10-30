import os
import json
import logging
import concurrent.futures
from datetime import datetime
import pytz
import numpy as np
import requests
import googlemaps
from google.cloud import firestore
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

# --- Configure Enterprise Logging ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()

# ---------------------------------------------------------
# 1. CLOUD INITIALIZATION (Firebase Only)
# ---------------------------------------------------------
db = None
gmaps = None


def initialize_clients():
    """Connect only when executing, so validation can run without cloud secrets."""
    global db, gmaps
    # Use short-lived Application Default Credentials from GitHub federation.
    # The destination is explicit: never fall back to the old Firebase project.
    db = firestore.Client(project="dar-traffic")
    key = os.getenv("MAPS_API_KEY")
    if not key or key == "YOUR_GOOGLE_API_KEY_HERE":
        raise RuntimeError("MAPS_API_KEY is required for traffic-aware collection")
    gmaps = googlemaps.Client(key=key, timeout=20, retry_timeout=30)


# ---------------------------------------------------------
# 2. DATA CONTRACTS (PYDANTIC SCHEMA)
# ---------------------------------------------------------
class TrafficSchema(BaseModel):
    """Strict data validation rules to prevent garbage data from entering Firebase."""

    schema_version: int = 2
    source: str = "google_distance_matrix"
    traffic_observed: bool = True
    distance_km: float = Field(..., gt=0)
    road_id: str
    name: str
    normal_mins: float = Field(
        ..., ge=0, description="Normal traffic time cannot be negative"
    )
    live_mins: float = Field(
        ..., ge=0, description="Live traffic time cannot be negative"
    )
    delay_mins: float = Field(..., ge=0, description="Delay cannot be negative")
    speed_kmh: float = Field(..., ge=0.0, description="Speed must be a positive float")
    status: str
    weather: str
    precipitation_mm: float = Field(0.0, ge=0.0, description="Precipitation rate in mm/hr")


# ---------------------------------------------------------
# 3. BOTTLENECK CONFIGURATION
# ---------------------------------------------------------
from config import ROADS


# ---------------------------------------------------------
# 4. WEATHER ENGINE
# ---------------------------------------------------------
def get_weather_for_all_roads(roads: list) -> dict:
    """
    Fetch weather for every road using the Open-Meteo bulk API.
    One HTTP request returns per-location results for all roads simultaneously.
    Returns: dict keyed by road['id'] -> (weather_str, precip_mm)
    """
    # Build comma-separated lat/lon lists from each road's start coordinate
    lats, lons, ids = [], [], []
    for road in roads:
        try:
            lat_str, lon_str = road["start"].split(",")
            lats.append(lat_str.strip())
            lons.append(lon_str.strip())
            ids.append(road["id"])
        except Exception:
            # Fallback: use Dar es Salaam city centre if coords are malformed
            lats.append("-6.7978")
            lons.append("39.2201")
            ids.append(road["id"])

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={','.join(lats)}"
        f"&longitude={','.join(lons)}"
        "&current=temperature_2m,precipitation,weather_code"
        "&timezone=Africa%2FDar_es_Salaam"
    )

    def parse_response(current: dict) -> tuple:
        temp   = current.get("temperature_2m", 28.0)
        code   = current.get("weather_code", 0)
        precip = float(current.get("precipitation", 0.0))
        # 61+ is actual Rain/Showers/Storms. 51-55 is just microscopic drizzle.
        if code >= 61 or precip >= 0.5:
            condition = "Rainy"
        elif code >= 4 or (50 <= code <= 55): # Treat light drizzle as cloudy
            condition = "Cloudy"
        else:
            condition = "Clear"
        return f"{temp}°C, {condition}", precip

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        result = {}

        # Single road returns a plain dict; multiple roads return a list
        if isinstance(data, list):
            for i, location_data in enumerate(data):
                road_id = ids[i]
                current = location_data["current"]
                result[road_id] = parse_response(current)
        else:
            # Only one location (fallback if API collapses to single response)
            current = data["current"]
            parsed = parse_response(current)
            for road_id in ids:
                result[road_id] = parsed

        logging.info(f"Weather fetched for {len(result)} road locations.")
        return result

    except Exception as e:
        logging.error(f"Bulk Weather API Error: {e}")
        # Return a safe default for all roads
        return {road["id"]: ("Unknown", 0.0) for road in roads}


# ---------------------------------------------------------
# 5. TRAFFIC ENGINE & FIREBASE SYNC
# ---------------------------------------------------------
def parse_traffic_element(element):
    """Preserve provider durations; never manufacture congestion from time or rain."""
    if element.get("status") != "OK":
        raise ValueError(f"Routing element status: {element.get('status')}")
    normal_seconds = float(element["duration"]["value"])
    live_seconds = float(element["duration_in_traffic"]["value"])
    distance_km = float(element["distance"]["value"]) / 1000
    if normal_seconds <= 0 or live_seconds <= 0 or distance_km <= 0:
        raise ValueError("Provider returned non-positive route measurements")
    return {
        "normal_mins": round(normal_seconds / 60, 2),
        "live_mins": round(live_seconds / 60, 2),
        "delay_mins": round(max(0, live_seconds - normal_seconds) / 60, 2),
        "speed_kmh": round(distance_km / (live_seconds / 3600), 2),
        "distance_km": distance_km,
    }


def update_smart_city(road, weather_info):
    weather, precip_mm = weather_info
    try:
        result = gmaps.distance_matrix(
            origins=road["start"], destinations=road["end"], mode="driving",
            departure_time="now", traffic_model="best_guess",
        )
        if result.get("status") != "OK":
            raise ValueError(f"Routing request status: {result.get('status')}")
        measurements = parse_traffic_element(result["rows"][0]["elements"][0])
        delay = measurements["delay_mins"]
        validated = TrafficSchema(
            road_id=road["id"], name=road["name"], **measurements,
            status="Smooth" if delay <= 3 else "Moderate" if delay <= 7 else "Heavy Jam",
            weather=weather, precipitation_mm=precip_mm,
        ).model_dump()
        validated["timestamp"] = firestore.SERVER_TIMESTAMP
        batch = db.batch()
        batch.set(db.collection("live_traffic").document(road["id"]), validated)
        batch.set(db.collection("traffic_history").document(), validated)
        batch.commit()
        logging.info("Synced %s: delay %.2f minutes", road["id"], delay)
        return True
    except Exception:
        logging.exception("Collection failed for %s; retaining last observation", road["id"])
        return False


# ---------------------------------------------------------
# 6. MAIN EXECUTION (CONCURRENT)
# ---------------------------------------------------------
if __name__ == "__main__":
    initialize_clients()
    road_weather_map = get_weather_for_all_roads(ROADS)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(
            lambda road: update_smart_city(road, road_weather_map.get(road["id"], ("Unknown", 0.0))),
            ROADS,
        ))
    succeeded = sum(results)
    logging.info("Collection complete: %s/%s roads", succeeded, len(ROADS))
    if succeeded != len(ROADS):
        raise SystemExit(1)
