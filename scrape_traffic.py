import os
import json
import logging
import concurrent.futures
from datetime import datetime
import pytz
import numpy as np
import requests
import googlemaps
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
import schedule
import time

# --- Configure Enterprise Logging ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()

# ---------------------------------------------------------
# 1. CLOUD INITIALIZATION (Firebase Only)
# ---------------------------------------------------------
firebase_secret = os.getenv("FIREBASE_KEY_JSON")

if firebase_secret:
    logging.info("Authenticating via Cloud Secrets...")
    cred_dict = json.loads(firebase_secret)
    cred = credentials.Certificate(cred_dict)
else:
    logging.info("Authenticating via local JSON file...")
    cred = credentials.Certificate("firebase-key.json")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

MAPS_API_KEY = os.getenv("MAPS_API_KEY")
gmaps = None


# ---------------------------------------------------------
# 2. DATA CONTRACTS (PYDANTIC SCHEMA)
# ---------------------------------------------------------
class TrafficSchema(BaseModel):
    """Strict data validation rules to prevent garbage data from entering Firebase."""

    road_id: str
    name: str
    normal_mins: int = Field(
        ..., ge=0, description="Normal traffic time cannot be negative"
    )
    live_mins: int = Field(
        ..., ge=0, description="Live traffic time cannot be negative"
    )
    delay_mins: int = Field(..., ge=0, description="Delay cannot be negative")
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
        data = requests.get(url, timeout=15).json()
        result = {}

        # Single road returns a plain dict; multiple roads return a list
        if isinstance(data, list):
            for i, location_data in enumerate(data):
                road_id = ids[i]
                current = location_data.get("current", {})
                result[road_id] = parse_response(current)
        else:
            # Only one location (fallback if API collapses to single response)
            current = data.get("current", {})
            parsed = parse_response(current)
            for road_id in ids:
                result[road_id] = parsed

        logging.info(f"Weather fetched for {len(result)} road locations.")
        return result

    except Exception as e:
        logging.error(f"Bulk Weather API Error: {e}")
        # Return a safe default for all roads
        return {road["id"]: ("28°C, Clear", 0.0) for road in roads}


# ---------------------------------------------------------
# 5. TRAFFIC ENGINE & FIREBASE SYNC
# ---------------------------------------------------------
def apply_traffic_congestion_model(road, base_live_mins, weather_str, precip_mm):
    dist_km = road["dist"]
    norm_m = max(1, int(round((dist_km / 45.0) * 60)))
    
    # EATS Timezone (Africa/Dar_es_Salaam)
    now_eats = datetime.now(pytz.timezone("Africa/Dar_es_Salaam"))
    hour = now_eats.hour
    day_of_week = now_eats.weekday()
    is_weekend = day_of_week >= 5

    # Rush hour intensity factor based on real Dar es Salaam traffic patterns
    congestion_factor = 1.0
    if not is_weekend:
        if 7 <= hour <= 9: # Morning Peak (Inbound to Commercial CBD)
            inbound_corridors = ["ubungo", "mwenge", "selander", "tazara", "kilwa_mbagala", "morocco_intersection", "sam_nujoma"]
            congestion_factor *= 2.8 if road["id"] in inbound_corridors else 1.5
        elif 16 <= hour <= 19: # Evening Peak (Outbound to Suburbs)
            outbound_corridors = ["mandela_buguruni", "tabata_dampo", "posta_to_kimara", "posta_to_tegeta", "posta_to_gongolamboto", "goba_massana"]
            congestion_factor *= 3.2 if road["id"] in outbound_corridors else 1.7
        elif 12 <= hour <= 14: # Lunch / Midday Traffic
            congestion_factor *= 1.3
        elif 22 <= hour or hour <= 5: # Late Night / Early Morning Flow
            congestion_factor *= 0.85
            
    # Rain Impact
    if precip_mm > 0.1 or "Rain" in str(weather_str):
        congestion_factor *= (1.3 + min(precip_mm * 0.05, 0.6))


    live_m = max(norm_m, int(round(base_live_mins * congestion_factor)))
    delay_m = max(0, live_m - norm_m)
    speed = round(dist_km / (live_m / 60.0), 1) if live_m > 0 else 0.0

    return norm_m, live_m, delay_m, speed



def update_smart_city(road, weather_info):
    weather, precip_mm = weather_info if isinstance(weather_info, tuple) else (str(weather_info), 0.0)
    try:
        raw_live_m = None

        # 1. Primary Engine: OSRM (Open Source Routing Machine - 100% Free, No Billing)
        try:
            start_lat, start_lon = road["start"].split(",")
            end_lat, end_lon = road["end"].split(",")
            osrm_url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=false"
            res = requests.get(osrm_url, timeout=10).json()

            if res.get("code") == "Ok" and res.get("routes"):
                route = res["routes"][0]
                live_sec = route["duration"]
                raw_live_m = max(1, int(round(live_sec / 60)))
        except Exception as osrm_err:
            logging.warning(f"OSRM engine lookup failed for {road['name']}: {osrm_err}")

        # 2. Fallback Engine: Google Maps Distance Matrix API
        if raw_live_m is None and gmaps is not None:
            result = gmaps.distance_matrix(
                origins=road["start"],
                destinations=road["end"],
                mode="driving",
                departure_time="now",
                traffic_model="best_guess",
            )

            element = result["rows"][0]["elements"][0]
            if element["status"] == "OK":
                raw_live_m = element["duration_in_traffic"]["value"] // 60
            else:
                logging.error(f"Google API Error for {road['name']}: {element['status']}")
                return

        if raw_live_m is None:
            logging.error(f"Unable to resolve traffic telemetry for {road['name']}")
            return

        norm_m, live_m, delay_m, speed = apply_traffic_congestion_model(road, raw_live_m, weather, precip_mm)

        status = (
            "Smooth" if delay_m <= 3 else "Moderate" if delay_m <= 7 else "Heavy Jam"
        )

        raw_data = {
            "road_id": road["id"],
            "name": road["name"],
            "normal_mins": norm_m,
            "live_mins": live_m,
            "delay_mins": delay_m,
            "speed_kmh": speed,
            "status": status,
            "weather": weather,
            "precipitation_mm": precip_mm,
        }

        # 🛡️ THE PYDANTIC BOUNCER: Validate the data before it touches the database
        validated_data = TrafficSchema(**raw_data).model_dump()

        # Once validated, append the Firestore timestamp
        validated_data["timestamp"] = firestore.SERVER_TIMESTAMP

        # HOT STORAGE
        db.collection("live_traffic").document(road["id"]).set(validated_data)
        # COLD STORAGE (Kept in Firebase so you don't lose history!)
        db.collection("traffic_history").add(validated_data)

        logging.info(f"✅ Firebase Synced | {road['name']}: {status} (+{delay_m}m)")

    except ValidationError as e:
        logging.error(
            f"❌ DATA CONTRACT FAILED for {road['name']}! Bad data blocked from DB:\n{e}"
        )
    except Exception as e:
        logging.error(f"Error syncing {road['name']}: {e}")


# ---------------------------------------------------------
# 6. MAIN EXECUTION (CONCURRENT)
# ---------------------------------------------------------
def run_scraper():
    global gmaps
    logging.info("Booting Smart City Engine with Pydantic Validation & OSRM Engine...")

    if MAPS_API_KEY and MAPS_API_KEY != "YOUR_GOOGLE_API_KEY_HERE":
        try:
            gmaps = googlemaps.Client(key=MAPS_API_KEY)
        except Exception:
            gmaps = None
    else:
        gmaps = None

    # Fetch per-road weather in a single bulk API call
    logging.info("Fetching per-road weather via Open-Meteo bulk API...")
    road_weather_map = get_weather_for_all_roads(ROADS)

    logging.info(
        "Initiating high-speed concurrent scraping (ThreadPoolExecutor)..."
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(update_smart_city, r, road_weather_map.get(r["id"], ("28°C, Clear", 0.0)))
            for r in ROADS
        ]
        concurrent.futures.wait(futures)

    logging.info("Sync Complete! Going back to sleep...")


if __name__ == "__main__":
    logging.info("Traffic Scraper Worker Started. Running 24/7 on Koyeb...")
    
    # Run the first scrape immediately when the server boots
    run_scraper()
    
    # Tell the script to run the job exactly every 20 minutes
    schedule.every(20).minutes.do(run_scraper)
    
    # Keep the server alive forever and check the clock
    while True:
        schedule.run_pending()
        time.sleep(1)


