import os
import json
import logging
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# --- Configure Enterprise Logging ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()

# ---------------------------------------------------------
# 1. CLOUD INITIALIZATION (Matched to your Scraper)
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


# ---------------------------------------------------------
# 2. DATA EXTRACTION & EXPORT
# ---------------------------------------------------------
def export_data():
    logging.info("Connecting to Firebase... Downloading 'traffic_history' collection.")

    try:
        # Stream all documents from the collection
        docs = db.collection("traffic_history").stream()

        data = []
        count = 0

        for doc in docs:
            row = doc.to_dict()

            # Firestore timestamps need to be converted to strings so Pandas can save them cleanly to CSV
            if "timestamp" in row and row["timestamp"] is not None:
                try:
                    row["timestamp"] = row["timestamp"].isoformat()
                except AttributeError:
                    pass  # If it's already a string, leave it alone

            data.append(row)
            count += 1

            # Print a progress update every 1,000 rows (helpful for massive datasets)
            if count % 1000 == 0:
                logging.info(f"Downloaded {count} records...")

        if not data:
            logging.warning(
                "No data found in 'traffic_history'. Are you sure the database is populated?"
            )
            return

        logging.info(f"Download complete. Total records fetched: {len(data)}")

        # ---------------------------------------------------------
        # 3. CSV GENERATION
        # ---------------------------------------------------------
        logging.info("Converting data to Pandas DataFrame and saving to CSV...")
        df = pd.DataFrame(data)

        # Save to CSV without the index column
        df.to_csv("historical_traffic.csv", index=False)

        logging.info(
            "✅ Success! Data successfully written to 'historical_traffic.csv'."
        )

    except Exception as e:
        logging.error(f"❌ Failed to export data: {e}")


if __name__ == "__main__":
    export_data()
