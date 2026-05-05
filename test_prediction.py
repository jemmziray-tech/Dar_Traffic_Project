import joblib
import pandas as pd

print("🤖 Waking up the AI Traffic Forecaster...")

# 1. Load the saved model (the "brain")
model = joblib.load("traffic_model.pkl")

# 2. Create a fake scenario to ask the AI about
# Let's ask: "What will the delay be on a Friday at 17:00 (5 PM) when it is Rainy?"
future_scenario = pd.DataFrame([{"Hour": 17, "Day": "Thursday", "Condition": "Rainy"}])

# 3. Ask the model to make a prediction
predicted_delay = model.predict(future_scenario)

# 4. Print the result
print(f"🚦 Scenario: Thursday at 5:00 PM (Rainy)")
print(f"🔮 AI Predicts a delay of: {predicted_delay[0]:.2f} minutes")
