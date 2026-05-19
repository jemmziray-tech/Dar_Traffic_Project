import os
import json
import logging
import concurrent.futures
import requests
import googlemaps
import firebase_admin
from firebase_admin import credentials, firestore
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

GOOGLE_API_KEY = os.getenv("MAPS_API_KEY")
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


# ---------------------------------------------------------
# 3. BOTTLENECK CONFIGURATION
# ---------------------------------------------------------
ROADS = [
    {
        "id": "ubungo",
        "name": "Morogoro Rd (Ubungo)",
        "start": "-6.7978,39.2201",
        "end": "-6.8040,39.2300",
        "dist": 1.8,
    },
    {
        "id": "mwenge",
        "name": "Bagamoyo Rd (Mwenge)",
        "start": "-6.7744,39.2431",
        "end": "-6.7631,39.2489",
        "dist": 1.5,
    },
    {
        "id": "selander",
        "name": "Ali Hassan Mwinyi",
        "start": "-6.7950,39.2750",
        "end": "-6.8050,39.2850",
        "dist": 1.4,
    },
    {
        "id": "tazara",
        "name": "Nyerere Rd (Tazara)",
        "start": "-6.8288,39.2600",
        "end": "-6.8400,39.2480",
        "dist": 1.7,
    },
    {
        "id": "mandela_buguruni",
        "name": "Mandela Rd (Port Link)",
        "start": "-6.8285,39.2435",
        "end": "-6.8335,39.2620",
        "dist": 2.5,
    },
    {
        "id": "kilwa_mbagala",
        "name": "Kilwa Rd (Mbagala)",
        "start": "-6.9050,39.2700",
        "end": "-6.8750,39.2800",
        "dist": 3.5,
    },
    {
        "id": "old_bagamoyo",
        "name": "Old Bagamoyo Rd (Victoria)",
        "start": "-6.7720,39.2550",
        "end": "-6.7820,39.2650",
        "dist": 1.5,
    },
    {
        "id": "sam_nujoma",
        "name": "Sam Nujoma Rd (Mwenge-Ubungo)",
        "start": "-6.7755,39.2435",
        "end": "-6.7975,39.2205",
        "dist": 4.2,
    },
    {
        "id": "uhuru_street",
        "name": "Uhuru Street (Ilala-Town)",
        "start": "-6.8220,39.2550",
        "end": "-6.8155,39.2820",
        "dist": 3.2,
    },
    {
        "id": "kariakoo",
        "name": "Kariakoo Market Grid",
        "start": "-6.8115,39.2725",
        "end": "-6.8210,39.2750",
        "dist": 1.1,
    },
    {
        "id": "posta_to_tegeta",
        "name": "Mega-Route: Posta to Tegeta (Bagamoyo Rd)",
        "start": "-6.8160,39.2880",
        "end": "-6.6430,39.1550",
        "dist": 22.0,
    },
    {
        "id": "posta_to_kimara",
        "name": "Mega-Route: Posta to Kimara (Morogoro Rd)",
        "start": "-6.8160,39.2880",
        "end": "-6.7800,39.1500",
        "dist": 17.5,
    },
    {
        "id": "posta_to_gongolamboto",
        "name": "Mega-Route: Posta to Gongo la Mboto (Nyerere Rd)",
        "start": "-6.8160,39.2880",
        "end": "-6.8850,39.1670",
        "dist": 18.0,
    },
    {
        "id": "tabata_dampo",
        "name": "Tabata Road (Mandela to Segerea)",
        "start": "-6.8150,39.2320",
        "end": "-6.8300,39.2050",
        "dist": 3.8,
    },
    {
        "id": "kamata_gerezani",
        "name": "Kamata / Gerezani (Port Entry)",
        "start": "-6.8280,39.2780",
        "end": "-6.8180,39.2850",
        "dist": 1.5,
    },
    {
        "id": "changombe_road",
        "name": "Chang'ombe Road (Temeke)",
        "start": "-6.8350,39.2700",
        "end": "-6.8550,39.2650",
        "dist": 2.5,
    },
    {
        "id": "morocco_intersection",
        "name": "Kawawa Rd (Morocco to Kinondoni)",
        "start": "-6.7820,39.2630",
        "end": "-6.7950,39.2580",
        "dist": 2.0,
    },
    {
        "id": "kigogo_roundabout",
        "name": "Kawawa Rd (Kigogo Choke)",
        "start": "-6.8120,39.2550",
        "end": "-6.8220,39.2500",
        "dist": 1.5,
    },
    {
        "id": "fire_upanga",
        "name": "UN Road (Fire to Upanga)",
        "start": "-6.8120,39.2780",
        "end": "-6.8020,39.2720",
        "dist": 1.2,
    },
    {
        "id": "mwai_kibaki",
        "name": "Mwai Kibaki Rd (Kawe to Mikocheni)",
        "start": "-6.7450,39.2350",
        "end": "-6.7650,39.2500",
        "dist": 3.5,
    },
    {
        "id": "sinza_mori",
        "name": "Sinza Road (Mori to Bamaga)",
        "start": "-6.7780,39.2350",
        "end": "-6.7700,39.2450",
        "dist": 2.0,
    },
    {
        "id": "goba_massana",
        "name": "Goba Road (Massana to Goba Center)",
        "start": "-6.7250,39.2150",
        "end": "-6.7150,39.1850",
        "dist": 4.0,
    },
]


# ---------------------------------------------------------
# 4. WEATHER ENGINE
# ---------------------------------------------------------
def get_weather():
    url = "https://api.open-meteo.com/v1/forecast?latitude=-6.7978&longitude=39.2201&current_weather=true"
    try:
        # 🚨 FIXED: Added a strict 10-second timeout to prevent infinite hanging
        data = requests.get(url, timeout=10).json()
        temp = data["current_weather"]["temperature"]
        code = data["current_weather"]["weathercode"]
        condition = "Clear" if code <= 3 else "Rainy" if code >= 51 else "Cloudy"
        return f"{temp}°C, {condition}"
    except Exception as e:
        logging.error(f"Weather API Error: {e}")
        return "Unknown Weather"


# ---------------------------------------------------------
# 5. TRAFFIC ENGINE & FIREBASE SYNC
# ---------------------------------------------------------
def update_smart_city(road, weather):
    try:
        result = gmaps.distance_matrix(
            origins=road["start"],
            destinations=road["end"],
            mode="driving",
            departure_time="now",
            traffic_model="best_guess",
        )

        element = result["rows"][0]["elements"][0]
        if element["status"] != "OK":
            logging.error(f"Google API Error for {road['name']}: {element['status']}")
            return

        live_m = element["duration_in_traffic"]["value"] // 60
        norm_m = element["duration"]["value"] // 60
        delay_m = max(0, live_m - norm_m)
        speed = round(road["dist"] / (live_m / 60), 1) if live_m > 0 else 0.0

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
        # If Pydantic catches a bad data type, it throws a ValidationError to stop the upload
        logging.error(
            f"❌ DATA CONTRACT FAILED for {road['name']}! Bad data blocked from DB:\n{e}"
        )
    except Exception as e:
        logging.error(f"Error syncing {road['name']}: {e}")


# ---------------------------------------------------------
# 6. MAIN EXECUTION (CONCURRENT)
# ---------------------------------------------------------
if __name__ == "__main__":
    logging.info("Booting Smart City Engine with Pydantic Validation...")

    if GOOGLE_API_KEY == "YOUR_GOOGLE_API_KEY_HERE" or not GOOGLE_API_KEY:
        logging.error(
            "You forgot to configure your Google API Key (MAPS_API_KEY) in the environment or GitHub Secrets!"
        )
    else:
        gmaps = googlemaps.Client(key=GOOGLE_API_KEY)
        current_weather = get_weather()

        logging.info(
            "Initiating high-speed concurrent scraping (ThreadPoolExecutor)..."
        )

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(update_smart_city, r, current_weather) for r in ROADS
            ]
            concurrent.futures.wait(futures)

        logging.info("Sync Complete!")
