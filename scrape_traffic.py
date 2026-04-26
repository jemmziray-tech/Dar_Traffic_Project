import os
import logging
from datetime import datetime
import requests
import googlemaps
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# --- Configure Enterprise Logging ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()

# ---------------------------------------------------------
# 1. CLOUD INITIALIZATION
# ---------------------------------------------------------
cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
gmaps = googlemaps.Client(key=GOOGLE_API_KEY)

# ---------------------------------------------------------
# 2. BOTTLENECK CONFIGURATION
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
        "start": "-6.7755,39.2435", # Mwenge side
        "end": "-6.7975,39.2205",   # Ubungo side
        "dist": 4.2,
    },
    {
        "id": "uhuru_street",
        "name": "Uhuru Street (Ilala-Town)",
        "start": "-6.8220,39.2550", # Ilala Boma
        "end": "-6.8155,39.2820",   # City Centre / Clock Tower
        "dist": 3.2,
    },
    {
        "id": "kariakoo",
        "name": "Kariakoo Market Grid",
        "start": "-6.8115,39.2725", # Msimbazi / Fire
        "end": "-6.8210,39.2750",   # Kariakoo Roundabout
        "dist": 1.1,
    },
]


# ---------------------------------------------------------
# 3. WEATHER ENGINE
# ---------------------------------------------------------
def get_weather():
    url = "https://api.open-meteo.com/v1/forecast?latitude=-6.7978&longitude=39.2201&current_weather=true"
    try:
        data = requests.get(url).json()
        temp = data["current_weather"]["temperature"]
        code = data["current_weather"]["weathercode"]
        condition = "Clear" if code <= 3 else "Rainy" if code >= 51 else "Cloudy"
        return f"{temp}°C, {condition}"
    except Exception as e:
        logging.error(f"Weather API Error: {e}")
        return "Unknown Weather"


# ---------------------------------------------------------
# 4. TRAFFIC ENGINE & FIREBASE SYNC
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

        traffic_data = {
            "road_id": road["id"],  # Fixed NameError bug here!
            "name": road["name"],
            "normal_mins": norm_m,
            "live_mins": live_m,
            "delay_mins": delay_m,
            "speed_kmh": speed,
            "status": status,
            "weather": weather,
            "timestamp": firestore.SERVER_TIMESTAMP,
        }

        # HOT STORAGE
        db.collection("live_traffic").document(road["id"]).set(traffic_data)
        # COLD STORAGE
        db.collection("traffic_history").add(traffic_data)

        logging.info(f"Firebase Synced | {road['name']}: {status} (+{delay_m}m)")

    except Exception as e:
        logging.error(f"Error syncing {road['name']}: {e}")


# ---------------------------------------------------------
# 5. MAIN EXECUTION
# ---------------------------------------------------------
if __name__ == "__main__":
    logging.info("Booting Smart City Engine...")

    if GOOGLE_API_KEY == "YOUR_GOOGLE_API_KEY_HERE" or not GOOGLE_API_KEY:
        logging.error("You forgot to configure your Google API Key in the .env file!")
    else:
        current_weather = get_weather()
        for r in ROADS:
            update_smart_city(r, current_weather)
        logging.info("Sync Complete!")
