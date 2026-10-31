"""Collect traffic estimates and write one live/history batch per corridor."""

import concurrent.futures
import logging
import math
import os
import uuid
from datetime import datetime, timedelta, timezone

import googlemaps
import requests
from google.cloud import firestore
from pydantic import BaseModel, ConfigDict, Field

from config import ROADS

logger = logging.getLogger(__name__)
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


class TrafficObservation(BaseModel):
    """Fields stored with each successful traffic observation."""

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


def collect_road(road, weather_info):
    weather, precip_mm = weather_info
    try:
        result = gmaps.distance_matrix(
            origins=road["start"],
            destinations=road["end"],
            mode="driving",
            departure_time="now",
            traffic_model="best_guess",
        )
        if result.get("status") != "OK":
            raise ValueError(f"Routing request status: {result.get('status')}")
        measurements = parse_traffic_element(result["rows"][0]["elements"][0])
        delay = measurements["delay_mins"]
        validated = TrafficObservation(
            road_id=road["id"],
            name=road["name"],
            **measurements,
            status="Smooth" if delay <= 3 else "Moderate" if delay <= 7 else "Heavy Jam",
            weather=weather,
            precipitation_mm=precip_mm,
        ).model_dump()
        validated["timestamp"] = firestore.SERVER_TIMESTAMP
        batch = db.batch()
        batch.set(db.collection("live_traffic").document(road["id"]), validated)
        batch.set(db.collection("traffic_history").document(), validated)
        batch.commit()
        logger.info("Synced %s: delay %.2f minutes", road["id"], delay)
        return True
    except Exception:
        logger.exception("Collection failed for %s; retaining last observation", road["id"])
        return False


def claim_collection(now=None):
    """Allow one execution per half-hour slot, with a lease against overlap."""
    now = now or datetime.now(timezone.utc)
    slot = int(now.timestamp()) // 1800
    owner = uuid.uuid4().hex
    reference = db.collection("_collector_state").document("collection")

    @firestore.transactional
    def claim(transaction):
        state = reference.get(transaction=transaction).to_dict() or {}
        if state.get("slot") == slot or state.get("lease_until", now) > now:
            return None
        transaction.set(
            reference,
            {
                "slot": slot,
                "owner": owner,
                "started_at": now,
                "lease_until": now + timedelta(minutes=10),
            },
        )
        return owner

    return claim(db.transaction())


def release_collection(owner):
    reference = db.collection("_collector_state").document("collection")

    @firestore.transactional
    def release(transaction):
        state = reference.get(transaction=transaction).to_dict() or {}
        if state.get("owner") == owner:
            transaction.update(reference, {"lease_until": datetime.now(timezone.utc)})

    release(db.transaction())


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    initialize_clients()
    owner = claim_collection()
    if not owner:
        logger.info(
            "Collection skipped: this slot was already started or another run holds the lease"
        )
        return 0
    try:
        weather = get_weather_for_all_roads(ROADS)
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = list(
                executor.map(
                    lambda road: collect_road(road, weather.get(road["id"], ("Unknown", None))),
                    ROADS,
                )
            )
        succeeded = sum(results)
        logger.info("Collection complete: %s/%s roads", succeeded, len(ROADS))
        return 0 if succeeded == len(ROADS) else 1
    finally:
        release_collection(owner)


if __name__ == "__main__":
    raise SystemExit(main())
