import requests
import csv
import os
from datetime import datetime

# Configuration
ROADS = [
    {
        "name": "Morogoro_Rd",
        "start": "-6.7978,39.2201",
        "end": "-6.8156,39.2863",
        "dist": 9.2,
        "file": "dar_morogoro_rd_traffic.csv",
    },
    {
        "name": "Bagamoyo_Rd",
        "start": "-6.6734,39.2135",
        "end": "-6.7845,39.2631",
        "dist": 13.5,
        "file": "dar_bagamoyo_rd_traffic.csv",
    },
]

TOMTOM_KEY = os.getenv("TOMTOM_API_KEY")


def get_weather():
    # Ubungo coordinates for a general Dar weather snapshot
    url = "https://api.open-meteo.com/v1/forecast?latitude=-6.7978&longitude=39.2201&current_weather=true"
    try:
        data = requests.get(url).json()
        temp = data["current_weather"]["temperature"]
        # Weather codes: 0=Clear, 1-3=Partly Cloudy, 51-67=Rain, 80-82=Showers
        code = data["current_weather"]["weathercode"]
        condition = "Clear" if code <= 3 else "Rainy" if code >= 51 else "Cloudy"
        return f"{temp}°C, {condition}"
    except:
        return "Unknown"


def get_traffic_data(road, weather):
    url = f"https://api.tomtom.com/routing/1/calculateRoute/{road['start']}:{road['end']}/json?key={TOMTOM_KEY}"
    try:
        data = requests.get(url).json()
        summary = data["routes"][0]["summary"]
        live_m = summary["travelTimeInSeconds"] // 60
        delay_m = summary["trafficDelayInSeconds"] // 60
        speed = round(road["dist"] / (live_m / 60), 1)
        status = (
            "Smooth" if delay_m <= 5 else "Moderate" if delay_m <= 15 else "Heavy Jam"
        )

        save_to_csv(
            road["file"],
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            live_m - delay_m,
            live_m,
            delay_m,
            speed,
            status,
            weather,
        )
        print(f"✅ {road['name']} updated. Weather: {weather}")
    except Exception as e:
        print(f"❌ Error: {e}")


def save_to_csv(fn, ts, norm, live, dly, spd, stat, wthr):
    exists = os.path.isfile(fn)
    with open(fn, "a", newline="") as f:
        writer = csv.writer(f)
        if not exists:
            writer.writerow(
                [
                    "Timestamp",
                    "Normal_Mins",
                    "Live_Mins",
                    "Delay_Mins",
                    "Avg_Speed_kmh",
                    "Status",
                    "Weather",
                ]
            )
        writer.writerow([ts, norm, live, dly, spd, stat, wthr])


if __name__ == "__main__":
    current_weather = get_weather()
    for r in ROADS:
        get_traffic_data(r, current_weather)
