from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import joblib
import os


# --- 1. Define the Expected Input (Data Validation) ---
# This tells the API exactly what data it needs from the user to make a prediction
class TrafficQuery(BaseModel):
    road_id: str
    Day: str
    Hour: float
    Condition: str


# --- 2. Initialize the App ---
app = FastAPI(
    title="Dar Traffic AI API",
    description="A REST API for predicting traffic delays in Dar es Salaam.",
    version="1.0.0",
)

# --- 3. Load the AI Model ---
# We load the brain once when the server starts up
if os.path.exists("traffic_model.pkl"):
    ai_model = joblib.load("traffic_model.pkl")
else:
    ai_model = None


# --- 4. Create the Prediction Endpoint ---
@app.post("/predict")
def predict_traffic(query: TrafficQuery):
    # Safety check: ensure the model actually loaded
    if ai_model is None:
        raise HTTPException(
            status_code=500, detail="AI Model is currently training and unavailable."
        )

    try:
        # Convert the incoming API request into a Pandas DataFrame for the AI
        input_data = pd.DataFrame(
            [
                {
                    "road_id": query.road_id,
                    "Hour": query.Hour,
                    "Day": query.Day,
                    "Condition": query.Condition,
                }
            ]
        )

        # Ask the AI for the prediction
        prediction = ai_model.predict(input_data)[0]

        # Send the answer back to the user
        return {
            "status": "success",
            "road": query.road_id,
            "predicted_delay_mins": round(prediction, 2),
        }

    except Exception as e:
        # If anything goes wrong, return a safe error message
        raise HTTPException(status_code=400, detail=str(e))


# --- 5. Create a Health Check Endpoint ---
@app.get("/")
def health_check():
    return {"message": "Dar Traffic API is online and ready."}
