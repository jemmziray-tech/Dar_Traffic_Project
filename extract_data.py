import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import json

try:
    cred = credentials.Certificate("firebase-key.json")
    firebase_admin.initialize_app(cred)
except ValueError:
    pass # App already initialized

db = firestore.client()
print("Fetching from Firestore...")
docs = db.collection("traffic_history").stream()
data = [doc.to_dict() for doc in docs]

df = pd.DataFrame(data)
if not df.empty:
    df.to_csv("historical_traffic_data.csv", index=False)
    print(f"Exported {len(df)} rows to historical_traffic_data.csv")
else:
    print("No data found.")
