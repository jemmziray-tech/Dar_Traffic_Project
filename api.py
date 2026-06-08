from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
import pandas as pd
import joblib
import os
from datetime import datetime

# --- 1. SECURITY SETUP ---
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

# This reads your key from the Environment Variable (set this in Render Dashboard!)
API_KEY = os.getenv("DAR_TRAFFIC_API_KEY", "dev-secret-key-123")

def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key

# --- 2. INPUT VALIDATION ---
class TrafficQuery(BaseModel):
    road_id: str
    timestamp: str  # Format: "2026-05-29 17:30:00"
    temperature_c: float
    is_raining: int
    delay_velocity: float

# --- 3. LOAD MODEL ---
app = FastAPI(title="Dar Traffic Enterprise API", version="3.1.0")
MODEL_PATH = "traffic_model.pkl"

# Load model safely
if os.path.exists(MODEL_PATH):
    ai_model = joblib.load(MODEL_PATH)
else:
    ai_model = None

# --- 4. ENDPOINTS ---
@app.get("/")
def read_root():
    return {"status": "online", "message": "Dar Traffic Enterprise API is running."}

@app.post("/predict", dependencies=[Depends(verify_api_key)])
def predict_traffic(query: TrafficQuery):
    if ai_model is None:
        raise HTTPException(status_code=500, detail="AI Model not found on server.")

    try:
        # Feature Engineering
        dt = pd.to_datetime(query.timestamp)
        input_data = pd.DataFrame([{
            "road_id": query.road_id,
            "hour": dt.hour,
            "day_of_week": dt.dayofweek,
            "is_weekend": 1 if dt.dayofweek >= 5 else 0,
            "is_rush_hour": 1 if dt.hour in [7, 8, 16, 17, 18, 19] else 0,
            "temp_c": query.temperature_c,
            "is_raining": query.is_raining,
            "delay_velocity": query.delay_velocity,
        }])

        # Prediction
        prediction = float(ai_model.predict(input_data)[0])
        predicted_delay = max(0.0, round(prediction, 1))

        # Explainable AI (XAI)
        explanation = "Traffic is expected to flow normally."
        if predicted_delay > 15:
            explanation = "🔴 Severe gridlock predicted."
        elif predicted_delay > 5:
            explanation = "🟡 Moderate delays expected."

        return {
            "status": "success",
            "prediction": {
                "road": query.road_id,
                "predicted_delay_mins": predicted_delay,
                "explanation": explanation
            }
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Prediction failed: {str(e)}")
