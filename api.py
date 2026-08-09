import os
import joblib
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# Try importing stable_baselines3 and the custom gym env
try:
    from stable_baselines3 import DQN
    from rl_env import TrafficEnv
    RL_AVAILABLE = True
except ImportError:
    RL_AVAILABLE = False

# Firebase for historical data (optional if not needed for endpoints)
import firebase_admin
from firebase_admin import credentials, firestore
import json

app = FastAPI(title="Dar Traffic AI Engine", version="1.0.0")

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the actual frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Models on Startup
rf_model = None
rl_model = None

@app.on_event("startup")
def load_models():
    global rf_model, rl_model
    if os.path.exists("traffic_model.pkl"):
        rf_model = joblib.load("traffic_model.pkl")
        print("[SUCCESS] XGBoost Model Loaded")
    else:
        print("[WARNING] traffic_model.pkl not found")

    if RL_AVAILABLE and os.path.exists("rl_traffic_model.zip"):
        rl_model = DQN.load("rl_traffic_model.zip")
        print("[SUCCESS] RL Model Loaded")
    else:
        print("[WARNING] rl_traffic_model.zip not found or RL dependencies missing")

# --- Schemas ---

class PredictRequest(BaseModel):
    road_ids: List[str]
    target_day: str
    target_time: str
    target_weather: str

class RlSimRequest(BaseModel):
    ns_queue: int
    ew_queue: int

# --- Helper Functions ---
DAYS_MAP = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}

def build_features_df(road_ids, target_day, target_time, target_weather):
    day_idx = DAYS_MAP.get(target_day, 0)
    is_wkd = 1 if day_idx >= 5 else 0
    h, m = map(int, target_time.split(":"))
    hour_fraction = h + (m / 60.0)
    int_hr = int(hour_fraction)
    is_rush = 1 if int_hr in [7, 8, 16, 17, 18, 19] else 0
    is_rain = 1 if "Rain" in str(target_weather) else 0
    precip = 5.0 if is_rain else 0.0

    return pd.DataFrame(
        [
            {
                "road_id": r_id,
                "hour": int_hr,
                "day_of_week": day_idx,
                "is_weekend": is_wkd,
                "is_rush_hour": is_rush,
                "temp_c": 28.0,
                "is_raining": is_rain,
                "precipitation_mm": precip,
                "delay_velocity": 0.0,
            }
            for r_id in road_ids
        ]
    )

# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"status": "online", "message": "Dar Traffic AI Engine API"}

@app.post("/predict/speed_ceiling")
def predict_delay(req: PredictRequest):
    """Predicts total traffic delay across a list of road segments."""
    if not rf_model:
        raise HTTPException(status_code=503, detail="XGBoost model is currently offline.")
    
    try:
        pred_df = build_features_df(req.road_ids, req.target_day, req.target_time, req.target_weather)
        segment_predictions = [max(0.0, float(val)) for val in rf_model.predict(pred_df)]
        total_delay = round(sum(segment_predictions), 1)
        
        status = "Smooth Flow"
        if total_delay > 10:
            status = "Moderate Congestion"
        if total_delay > 25:
            status = "Heavy Gridlock"
            
        return {
            "total_delay_minutes": total_delay,
            "status": status,
            "segment_breakdown": dict(zip(req.road_ids, [round(p, 1) for p in segment_predictions]))
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/rl/simulate")
def rl_action(req: RlSimRequest):
    """Asks the trained RL Agent what the next optimal light action is."""
    if not rl_model:
        raise HTTPException(status_code=503, detail="RL model is currently offline.")
    
    try:
        # Observation space in our env is [ns_queue, ew_queue]
        obs = np.array([req.ns_queue, req.ew_queue], dtype=np.float32)
        action, _ = rl_model.predict(obs, deterministic=True)
        action_int = int(action)
        
        return {
            "optimal_action_id": action_int,
            "optimal_action_str": "NS_GREEN" if action_int == 0 else "EW_GREEN"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/data/history")
def get_history(limit: int = 50):
    """Fetches recent traffic telemetry from Firebase."""
    try:
        firebase_secret = os.getenv("FIREBASE_KEY_JSON")
        if not firebase_admin._apps:
            if firebase_secret:
                cred_dict = json.loads(firebase_secret)
                cred = credentials.Certificate(cred_dict)
            else:
                cred = credentials.Certificate("firebase-key.json")
            firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        docs = db.collection("traffic_history").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit).stream()
        
        data = [doc.to_dict() for doc in docs]
        return {"count": len(data), "records": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
