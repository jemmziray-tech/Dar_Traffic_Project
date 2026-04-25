import googlemaps
import firebase_admin
from firebase_admin import credentials, firestore
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------
# 1. CLOUD INITIALIZATION
# ---------------------------------------------------------
# Connect to Firebase using your secret JSON key
cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Connect to Google Maps
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
    except:
        return "Unknown Weather"


# ---------------------------------------------------------
# 4. TRAFFIC ENGINE & FIREBASE SYNC
# ---------------------------------------------------------
def update_smart_city(road, weather):
    try:
        # Ask Google for Live Data
        result = gmaps.distance_matrix(
            origins=road["start"],
            destinations=road["end"],
            mode="driving",
            departure_time="now",
            traffic_model="best_guess",
        )

        element = result["rows"][0]["elements"][0]
        if element["status"] != "OK":
            print(f"❌ Google API Error for {road['name']}: {element['status']}")
            return

        # Calculate Math
        live_m = element["duration_in_traffic"]["value"] // 60
        norm_m = element["duration"]["value"] // 60
        delay_m = max(0, live_m - norm_m)
        speed = round(road["dist"] / (live_m / 60), 1) if live_m > 0 else 0.0

        # Determine Status
        status = (
            "Smooth" if delay_m <= 3 else "Moderate" if delay_m <= 7 else "Heavy Jam"
        )

        # Build the Data Payload
        traffic_data = {
            "road_id": road_id,
            "name": road["name"],
            "normal_mins": norm_m,
            "live_mins": live_m,
            "delay_mins": delay_m,
            "speed_kmh": speed,
            "status": status,
            "weather": weather,
            # SERVER_TIMESTAMP is crucial: it uses Google's perfect internal clock
            "timestamp": firestore.SERVER_TIMESTAMP,
        }

        # --- HOT / COLD STORAGE STRATEGY ---

        # HOT STORAGE: Overwrite the live document (For your App/Dashboard)
        db.collection("live_traffic").document(road["id"]).set(traffic_data)

        # COLD STORAGE: Add a new log for Machine Learning History
        db.collection("traffic_history").add(traffic_data)

        print(f"✅ Firebase Synced | {road['name']}: {status} (+{delay_m}m)")

    except Exception as e:
        print(f"❌ Error syncing {road['name']}: {e}")


# ---------------------------------------------------------
# 5. MAIN EXECUTION
# ---------------------------------------------------------
if __name__ == "__main__":
    print(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Booting Smart City Engine..."
    )

    if GOOGLE_API_KEY == "YOUR_GOOGLE_API_KEY_HERE":
        print("⚠️ ERROR: You forgot to paste your Google API Key on line 17!")
    else:
        current_weather = get_weather()
        for r in ROADS:
            update_smart_city(r, current_weather)
        print("🎉 Sync Complete!")
