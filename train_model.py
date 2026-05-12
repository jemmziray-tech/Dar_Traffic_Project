import os
import csv
import json
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
from sklearn.metrics import mean_absolute_error, r2_score

print("🚀 Booting Advanced Enterprise AI Training Pipeline...")

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

# Filter the data to ONLY include our 10 target roads
df = df[df["road_id"].isin(TARGET_ROADS)]

print(f"✅ Extracted {len(df)} total rows of raw data.")

# --- 3. Advanced Data Cleaning & Outlier Rejection ---
print("⚙️ Executing Data Sanitization & Feature Engineering...")

# 🛡️ OUTLIER REJECTION: Drop impossible delays (e.g., API glitches > 3 hours)
# This prevents the AI from learning garbage data
initial_row_count = len(df)
df = df[df["delay_mins"] <= 180]
if len(df) < initial_row_count:
    print(
        f"🗑️ Removed {initial_row_count - len(df)} corrupted outlier records (delays > 3 hours)."
    )

# Clean negative delays (just in case they slipped past the Pydantic scraper)
df["delay_mins"] = df["delay_mins"].clip(lower=0)

df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_convert("Africa/Dar_es_Salaam")
df["Hour"] = df["timestamp"].dt.hour + (df["timestamp"].dt.minute / 60.0)
df["Day"] = df["timestamp"].dt.day_name()
df["Condition"] = df["weather"].apply(
    lambda x: x.split(", ")[1] if isinstance(x, str) and ", " in x else "Clear"
)

X = df[["road_id", "Hour", "Day", "Condition"]]
y = df["delay_mins"]

if len(df) < 500:
    print(
        f"⚠️ Warning: Dataset is very small ({len(df)} rows). Anti-Overfitting protocols engaged."
    )

# --- 4. Build the Enterprise Machine Learning Pipeline ---
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

# 🧠 ANTI-OVERFITTING AI CORE
# n_estimators=150: Creates 150 separate decision trees for better accuracy
# max_depth=20: Stops trees from memorizing the data (prevents the -324 min glitch)
# min_samples_leaf=2: Requires at least 2 data points to make a conclusion
# n_jobs=-1: Uses maximum server CPU power
model_pipeline = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        (
            "regressor",
            RandomForestRegressor(
                n_estimators=150,
                max_depth=20,
                min_samples_split=4,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1,
            ),
        ),
    ]
)

# --- 5. Train, Evaluate, and Save ---
print("🧠 Training the Advanced Random Forest AI Engine...")
model_pipeline.fit(X_train, y_train)

predictions = model_pipeline.predict(X_test)
mae = mean_absolute_error(y_test, predictions)
r2 = r2_score(y_test, predictions)

print("=" * 40)
print(f"🎯 Global MAE: Off by {mae:.2f} minutes.")
print(f"🎯 Model R² Score: {r2:.2f}")
print("=" * 40)

joblib.dump(model_pipeline, "traffic_model.pkl")
print("💾 Securely saved 'traffic_model.pkl'!")

# --- 6. Save Metrics to Track MLOps Drift ---
print("📈 Logging MLOps drift metrics...")
metrics_file = "model_metrics.csv"
file_exists = os.path.isfile(metrics_file)

with open(metrics_file, mode="a", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)

    if not file_exists:
        writer.writerow(["Date", "Total_Rows_Trained", "MAE_Minutes", "R2_Score"])

    today_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    writer.writerow([today_date, len(df), round(mae, 2), round(r2, 2)])

print("✅ Pipeline execution fully complete!")
