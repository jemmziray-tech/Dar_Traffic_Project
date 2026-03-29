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
    {
        "name": "Ali_Hassan_Mwinyi_Rd",
        "start": "-6.7720,39.2590",
        "end": "-6.8005,39.2818",
        "dist": 4.5,
        "file": "dar_ali_hassan_mwinyi_traffic.csv",
    },
    {
        "name": "Msimbazi_St_Kariakoo",
        "start": "-6.8164,39.2730",
        "end": "-6.8248,39.2785",
        "dist": 1.5,
        "file": "dar_msimbazi_kariakoo_traffic.csv",
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
    # Added &traffic=true and &departAt=now to force real-time data
    url = f"https://api.tomtom.com/routing/1/calculateRoute/{road['start']}:{road['end']}/json?key={TOMTOM_KEY}&traffic=true&departAt=now"

    try:
        data = requests.get(url).json()
        summary = data["routes"][0]["summary"]

        # total travel time including current traffic
        live_m = summary["travelTimeInSeconds"] // 60
        # actual delay compared to a clear road
        delay_m = summary["trafficDelayInSeconds"] // 60

        # 'Normal' is the time it SHOULD take if there was zero traffic
        # TomTom calls this 'noTrafficTravelTimeInSeconds' in some versions,
        # but 'live - delay' is a solid way to calculate it here.
        norm_m = live_m - delay_m

        speed = round(road["dist"] / (live_m / 60), 1)

        # Enhanced status logic
        if delay_m == 0:
            status = "Smooth"
        elif delay_m <= 7:
            status = "Moderate"
        else:
            status = "Heavy Jam"

        save_to_csv(
            road["file"],
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            norm_m,
            live_m,
            delay_m,
            speed,
            status,
            weather,
        )
        print(
            f"✅ {road['name']} updated: {status} ({delay_m}m delay). Speed: {speed}kmh"
        )

    except Exception as e:
        print(f"❌ Error on {road['name']}: {e}")


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
