import os
import csv
import json
import numpy as np
import pandas as pd
import joblib
from datetime import datetime

# Firebase
import firebase_admin
from firebase_admin import credentials, firestore

# Scikit-Learn & Advanced ML
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, r2_score
import category_encoders as ce
from xgboost import XGBRegressor

print("🚀 Booting Advanced Enterprise AI Training Pipeline (V3 XGBoost + Velocity)...")

# --- 1. Define Target Roads ---
TARGET_ROADS = [
    "ubungo",
    "mwenge",
    "selander",
    "tazara",
    "mandela_buguruni",
    "kilwa_mbagala",
    "old_bagamoyo",
    "sam_nujoma",
    "uhuru_street",
    "posta_to_tegeta",
    "posta_to_kimara",
    "posta_to_gongolamboto",
    "tabata_dampo",
    "kamata_gerezani",
    "changombe_road",
    "morocco_intersection",
    "kigogo_roundabout",
    "fire_upanga",
    "mwai_kibaki",
    "sinza_mori",
    "goba_massana",
]

# --- 2. Connect to Firebase & Fetch Data ---
print("📥 Fetching historical telemetry from Firebase...")

firebase_secret = os.getenv("FIREBASE_KEY_JSON")

if not firebase_admin._apps:
    if firebase_secret:
        print("🔒 Authenticating via Cloud Secrets...")
        cred_dict = json.loads(firebase_secret)
        cred = credentials.Certificate(cred_dict)
    else:
        print("💻 Authenticating via local JSON file...")
        cred = credentials.Certificate("firebase-key.json")

    firebase_admin.initialize_app(cred)

db = firestore.client()
docs = db.collection("traffic_history").stream()

# Convert database records to a Pandas DataFrame
df = pd.DataFrame([doc.to_dict() for doc in docs])

if df.empty:
    print("❌ CRITICAL ERROR: No data found in Firebase. Exiting pipeline.")
    exit(1)

# Filter the data to ONLY include our target roads
df = df[df["road_id"].isin(TARGET_ROADS)]

print(f"✅ Extracted {len(df)} total rows of raw data.")

# --- 3. Advanced Feature Engineering & Sanitization ---
print("⚙️ Executing Data Sanitization & Feature Engineering...")

# 🛡️ OUTLIER REJECTION: Drop impossible delays (API glitches > 3 hours)
initial_row_count = len(df)
df = df[df["delay_mins"] <= 180]
df["delay_mins"] = df["delay_mins"].clip(lower=0)
if len(df) < initial_row_count:
    print(f"🗑️ Removed {initial_row_count - len(df)} corrupted outlier records.")

# 🕒 TEMPORAL ENGINEERING
df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_convert("Africa/Dar_es_Salaam")
df["hour"] = df["timestamp"].dt.hour
df["day_of_week"] = df["timestamp"].dt.dayofweek
df["is_weekend"] = df["day_of_week"].apply(lambda x: 1 if x >= 5 else 0)
# Define Dar es Salaam Rush Hours (7-9 AM, 4-7 PM)
df["is_rush_hour"] = df["hour"].apply(lambda x: 1 if x in [7, 8, 16, 17, 18, 19] else 0)

# ⛈️ WEATHER ENGINEERING (Extracting text into math)
df["temp_c"] = df["weather"].astype(str).str.extract(r"([0-9.]+)").astype(float)
df["temp_c"] = df["temp_c"].fillna(25.0)  # Default to 25C if sensor fails
df["condition"] = df["weather"].apply(
    lambda x: str(x).split(", ")[1] if ", " in str(x) else "Clear"
)
df["is_raining"] = df["condition"].apply(lambda x: 1 if "Rain" in str(x) else 0)

# 🌪️ TRAFFIC VELOCITY ENGINEERING (The V3 Upgrade)
print("🌪️ Calculating 20-Minute Traffic Velocity (Delta)...")
# Sort chronologically so we can compare a row to the row exactly 20 mins prior
df = df.sort_values(by=["road_id", "timestamp"])
df["previous_delay"] = df.groupby("road_id")["delay_mins"].shift(1)
# Calculate momentum: positive = getting worse, negative = clearing
df["delay_velocity"] = df["delay_mins"] - df["previous_delay"]
df["delay_velocity"] = df["delay_velocity"].fillna(0)  # Fill first rows with 0


# Define our features.
features = [
    "road_id",
    "hour",
    "day_of_week",
    "is_weekend",
    "is_rush_hour",
    "temp_c",
    "is_raining",
    "delay_velocity",
]
X = df[features]
y = df["delay_mins"]

# --- 4. Build the Enterprise Machine Learning Pipeline ---
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# 🎯 SAMPLE WEIGHTING: Force the AI to care 5x more about severe gridlocks (>15 mins)
train_weights = np.where(y_train > 15, 5.0, 1.0)

# 🧮 PREPROCESSOR: Target Encoding for roads, Passthrough for numbers
preprocessor = ColumnTransformer(
    transformers=[
        (
            "num",
            "passthrough",
            [
                "hour",
                "day_of_week",
                "is_weekend",
                "is_rush_hour",
                "temp_c",
                "is_raining",
                "delay_velocity",
            ],
        ),
        ("cat", ce.TargetEncoder(), ["road_id"]),
    ]
)

# ⚡ XGBOOST CORE
model_pipeline = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        (
            "regressor",
            XGBRegressor(
                n_estimators=500,
                learning_rate=0.05,
                max_depth=6,
                subsample=0.8,
                random_state=42,
                n_jobs=-1,
            ),
        ),
    ]
)

# --- 5. Train, Evaluate, and Save ---
print("🧠 Training the XGBoost AI Engine with Sample Weights...")
# We pass the sample weights directly into the XGBoost step of the pipeline
model_pipeline.fit(X_train, y_train, regressor__sample_weight=train_weights)

predictions = model_pipeline.predict(X_test)
mae = mean_absolute_error(y_test, predictions)
r2 = r2_score(y_test, predictions)

print("=" * 40)
print(f"🎯 Global MAE: Off by {mae:.2f} minutes.")
print(f"🎯 Model R² Score: {r2:.3f}")
print("=" * 40)

joblib.dump(model_pipeline, "traffic_model.pkl")
print("💾 Securely saved 'traffic_model.pkl'! (Overwritten with V3 Brain)")

# --- 6. Save Metrics to Track MLOps Drift ---
print("📈 Logging MLOps drift metrics...")
metrics_file = "model_metrics.csv"
file_exists = os.path.isfile(metrics_file)

with open(metrics_file, mode="a", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)

    if not file_exists:
        writer.writerow(["Date", "Total_Rows_Trained", "MAE_Minutes", "R2_Score"])

    today_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    writer.writerow([today_date, len(df), round(mae, 2), round(r2, 3)])

print("✅ Pipeline execution fully complete!")
