import requests
import csv
import os
from datetime import datetime

# Configuration: MICRO-SEGMENTS
# We target 1-2km bottleneck zones so delays don't get "averaged out"
ROADS = [
    {
        "name": "Morogoro_Rd_Ubungo_Bottleneck",
        "start": "-6.7978,39.2201",  # Just before Ubungo Interchange
        "end": "-6.8040,39.2300",  # Just past the interchange
        "dist": 1.8,  # Distance shortened to 1.8km
        "file": "dar_morogoro_rd_traffic.csv",
    },
    {
        "name": "Bagamoyo_Rd_Mwenge_Bottleneck",
        "start": "-6.7744,39.2431",  # Just before Mlimani City turnoff
        "end": "-6.7631,39.2489",  # Just past Mwenge bus stand
        "dist": 1.5,  # Distance shortened to 1.5km
        "file": "dar_bagamoyo_rd_traffic.csv",
    },
    {
        "name": "Ali_Hassan_Mwinyi_Selander",
        "start": "-6.7950,39.2750",  # Approaching Selander Bridge
        "end": "-6.8050,39.2850",  # Past the bridge into city center
        "dist": 1.4,  # Distance shortened to 1.4km
        "file": "dar_ali_hassan_mwinyi_traffic.csv",
    },
    {
        "name": "Msimbazi_St_Kariakoo",
        "start": "-6.8164,39.2730",  # Kariakoo entry
        "end": "-6.8248,39.2785",  # Kariakoo exit
        "dist": 1.5,  # Your original distance was perfect here!
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
    # Added routeType=fastest and travelMode=car for higher accuracy probe data
    url = f"https://api.tomtom.com/routing/1/calculateRoute/{road['start']}:{road['end']}/json?key={TOMTOM_KEY}&traffic=true&departAt=now&routeType=fastest&travelMode=car"

    try:
        data = requests.get(url).json()
        summary = data["routes"][0]["summary"]

        # total travel time including current traffic
        live_m = summary["travelTimeInSeconds"] // 60
        # actual delay compared to a clear road
        delay_m = summary["trafficDelayInSeconds"] // 60

        # 'Normal' is the time it SHOULD take if there was zero traffic
        norm_m = live_m - delay_m

        # Calculate speed. Prevent division by zero if live_m is incredibly short.
        if live_m > 0:
            speed = round(road["dist"] / (live_m / 60), 1)
        else:
            speed = 0.0

        # Enhanced status logic (Tuned for micro-segments)
        # A 5-minute delay on a 1km road is massive!
        if delay_m == 0:
            status = "Smooth"
        elif delay_m <= 3:
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
    # Safety check so the script doesn't crash if the API key isn't set
    if not TOMTOM_KEY:
        print("⚠️ ERROR: TOMTOM_API_KEY environment variable is not set!")
        print(
            "If you are running this locally, hardcode your key temporarily for testing."
        )
    else:
        current_weather = get_weather()
        for r in ROADS:
            get_traffic_data(r, current_weather)
