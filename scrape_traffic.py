import requests
import csv
import os
from datetime import datetime, timedelta

# 🔐 Cloud Security: Read the API key from GitHub Secrets
API_KEY = os.getenv("TOMTOM_API_KEY")

START_POINT = "-6.7865,39.2205"
END_POINT = "-6.8153,39.2846"

URL = f"https://api.tomtom.com/routing/1/calculateRoute/{START_POINT}:{END_POINT}/json"


def get_live_traffic():
    # Dar es Salaam is UTC+3
    dar_time = datetime.utcnow() + timedelta(hours=3)
    print(
        f"\n[{dar_time.strftime('%H:%M:%S')}] 🚦 Checking Morogoro Rd traffic from the Cloud..."
    )

    if not API_KEY:
        print("❌ ERROR: API Key not found! Make sure GitHub Secrets are set.")
        return

    params = {"key": API_KEY, "traffic": "true", "routeType": "fastest"}

    try:
        response = requests.get(URL, params=params)
        data = response.json()

        if "routes" not in data:
            print(f"❌ API Error: {data.get('errorText', 'Unknown Error')}")
            return

        summary = data["routes"][0]["summary"]

        live_time_seconds = summary.get("travelTimeInSeconds", 0)
        delay_seconds = summary.get("trafficDelayInSeconds", 0)

        live_time_mins = live_time_seconds // 60
        delay_mins = delay_seconds // 60
        normal_time_mins = (live_time_seconds - delay_seconds) // 60

        timestamp = dar_time.strftime("%Y-%m-%d %H:%M:%S")

        print(
            f"✅ Normal: {normal_time_mins}m | Live: {live_time_mins}m | Delay: {delay_mins}m"
        )
        save_to_csv(timestamp, normal_time_mins, live_time_mins, delay_mins)

    except Exception as e:
        print(f"❌ Request failed: {e}")


def save_to_csv(timestamp, normal_time, live_time, delay):
    filename = "dar_morogoro_rd_traffic.csv"
    file_exists = os.path.isfile(filename) and os.stat(filename).st_size > 0

    with open(filename, mode="a", newline="") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(
                ["Timestamp", "Normal_Time_Mins", "Live_Time_Mins", "Delay_Mins"]
            )
        writer.writerow([timestamp, normal_time, live_time, delay])


if __name__ == "__main__":
    # NO LOOP! GitHub will run this file once every 15 minutes.
    get_live_traffic()
