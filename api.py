from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import joblib
import os
from datetime import datetime


# --- 1. Define the Expected Input (Data Validation) ---
# This is what the WhatsApp Bot or Dashboard will send to the API
class TrafficQuery(BaseModel):
    road_id: str
    timestamp: str  # e.g., "2026-05-29 17:30:00"
    temperature_c: float  # e.g., 25.2
    is_raining: int  # 1 if raining, 0 if clear
    delay_velocity: float  # The change in delay over the last 20 mins (e.g., 5.0 means getting worse)


# --- 2. Initialize the App ---
app = FastAPI(
    title="Dar Traffic Enterprise AI API",
    description="XGBoost-powered REST API for predicting traffic delays with Explainable AI.",
    version="3.0.0",
)

# --- 3. Load the AI Model ---
MODEL_PATH = "traffic_model.pkl"
if os.path.exists(MODEL_PATH):
    print("🧠 Loading XGBoost V3 Engine...")
    ai_model = joblib.load(MODEL_PATH)
else:
    print("⚠️ WARNING: traffic_model.pkl not found! Did you run train_model.py?")
    ai_model = None


# --- 4. Create the Prediction Endpoint ---
@app.post("/predict")
def predict_traffic(query: TrafficQuery):
    # Safety check: ensure the model actually loaded
    if ai_model is None:
        raise HTTPException(
            status_code=500, detail="AI Model is offline. Please train the model first."
        )

    try:
        # ---------------------------------------------------------
        # A. FEATURE ENGINEERING (Translating user input for the AI)
        # ---------------------------------------------------------
        try:
            dt = pd.to_datetime(query.timestamp)
        except Exception:
            raise HTTPException(
                status_code=400, detail="Invalid timestamp. Use YYYY-MM-DD HH:MM:SS"
            )

        hour = dt.hour
        day_of_week = dt.dayofweek

        # Calculate the mathematical flags
        is_weekend = 1 if day_of_week >= 5 else 0
        is_rush_hour = 1 if hour in [7, 8, 16, 17, 18, 19] else 0

        # Construct the exact DataFrame the XGBoost pipeline expects
        input_data = pd.DataFrame(
            [
                {
                    "road_id": query.road_id,
                    "hour": hour,
                    "day_of_week": day_of_week,
                    "is_weekend": is_weekend,
                    "is_rush_hour": is_rush_hour,
                    "temp_c": query.temperature_c,
                    "is_raining": query.is_raining,
                    "delay_velocity": query.delay_velocity,
                }
            ]
        )

        # ---------------------------------------------------------
        # B. THE AI PREDICTION
        # ---------------------------------------------------------
        prediction = float(ai_model.predict(input_data)[0])

        # Ensure the AI doesn't predict "negative" time due to statistical smoothing
        predicted_delay = max(0.0, round(prediction, 1))

        # ---------------------------------------------------------
        # C. EXPLAINABLE AI (XAI) - Building Human Trust
        # ---------------------------------------------------------
        reasoning = []
        if is_rush_hour:
            reasoning.append("peak rush hour volume")
        if query.is_raining:
            reasoning.append("adverse weather conditions (Rain)")
        if query.delay_velocity > 5:
            reasoning.append(
                "a rapidly compounding bottleneck (Traffic Velocity is high)"
            )

        explanation = "Traffic is expected to flow normally."
        if predicted_delay > 15:
            factors = (
                " compounded by ".join(reasoning)
                if reasoning
                else "heavy localized congestion"
            )
            explanation = f"🔴 Severe gridlock predicted due to {factors}."
        elif predicted_delay > 5:
            explanation = "🟡 Moderate delays expected. Proceed with caution."

        # ---------------------------------------------------------
        # D. RETURN THE ENTERPRISE JSON PAYLOAD
        # ---------------------------------------------------------
        return {
            "status": "success",
            "telemetry_analyzed": {
                "road": query.road_id,
                "timestamp_processed": dt.strftime("%Y-%m-%d %H:%M:%S"),
            },
            "prediction": {
                "predicted_delay_mins": predicted_delay,
                # Applying a standard +/- 3 minute confidence band based on our MAE score!
                "confidence_interval": f"{max(0, round(predicted_delay - 3.0, 1))} to {round(predicted_delay + 3.0, 1)} mins",
            },
            "xai_explanation": explanation,
        }

    except Exception as e:
        # If anything goes wrong, return a safe error message
        raise HTTPException(status_code=400, detail=f"Prediction failed: {str(e)}")
