import os
import csv
from datetime import datetime
import pandas as pd
import joblib
import firebase_admin
from firebase_admin import credentials, firestore
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error

print("🚀 Starting Global AI Training Pipeline (10 Roads | 15-Min Precision)...")

# --- 1. Define Target Roads ---
TARGET_ROADS = [
    "kilwa_mbagala",
    "mandela_buguruni",
    "mwenge",
    "old_bagamoyo",
    "selander",
    "tazara",
    "ubungo",
    "sam_nujoma",
    "uhuru_street",
    "kariakoo",
]

# --- 2. Connect to Firebase & Fetch Data ---
print("📥 Fetching historical data from Firebase...")
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-key.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()
docs = db.collection("traffic_history").stream()

# Convert database records to a Pandas DataFrame
df = pd.DataFrame([doc.to_dict() for doc in docs])

# Filter the data to ONLY include our 10 target roads
df = df[df["road_id"].isin(TARGET_ROADS)]

print("\n📊 Data Distribution per Road:")
print(df["road_id"].value_counts())
print("-" * 30)

if len(df) < 200:
    print(
        f"⚠️ Warning: Only {len(df)} total rows found across 10 roads. The AI will get smarter as this grows!"
    )

# --- 3. Feature Engineering (Data Cleaning) ---
print("⚙️ Preparing time and weather features...")

df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_convert("Africa/Dar_es_Salaam")
df["Hour"] = df["timestamp"].dt.hour + (df["timestamp"].dt.minute / 60.0)
df["Day"] = df["timestamp"].dt.day_name()
df["Condition"] = df["weather"].apply(
    lambda x: x.split(", ")[1] if isinstance(x, str) and ", " in x else "Clear"
)

X = df[["road_id", "Hour", "Day", "Condition"]]
y = df["delay_mins"]

# --- 4. Build the Machine Learning Pipeline ---
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

preprocessor = ColumnTransformer(
    transformers=[
        ("num", "passthrough", ["Hour"]),
        (
            "cat",
            OneHotEncoder(handle_unknown="ignore"),
            ["road_id", "Day", "Condition"],
        ),
    ]
)

model_pipeline = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        ("regressor", RandomForestRegressor(n_estimators=100, random_state=42)),
    ]
)

# --- 5. Train, Evaluate, and Save ---
print("🧠 Training the Global Random Forest AI...")
model_pipeline.fit(X_train, y_train)

predictions = model_pipeline.predict(X_test)
mae = mean_absolute_error(y_test, predictions)
print(
    f"🎯 Global Accuracy: Predictions across all 10 roads are typically off by {mae:.2f} minutes."
)

joblib.dump(model_pipeline, "traffic_model.pkl")
print("💾 Global Model successfully saved as 'traffic_model.pkl'!")

# --- 6. Save Metrics to Track Learning Over Time ---
print("📈 Logging model metrics...")
metrics_file = "model_metrics.csv"
file_exists = os.path.isfile(metrics_file)

with open(metrics_file, mode="a", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    if not file_exists:
        writer.writerow(["Date", "Total_Rows_Trained", "MAE_Minutes"])

    today_date = datetime.now().strftime("%Y-%m-%d")
    writer.writerow([today_date, len(df), round(mae, 2)])

print("✅ Metrics logged successfully!")
