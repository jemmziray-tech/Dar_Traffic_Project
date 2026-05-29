import os
import pandas as pd
from datetime import datetime
import streamlit as st
import joblib
import google.generativeai as genai
from dotenv import load_dotenv

# --- 0. SECURE ENVIRONMENT ---
load_dotenv()

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="AI Route Predictor", layout="wide", page_icon=":material/online_prediction:")

st.markdown("""
<style>
div[data-testid="stMetricValue"] { font-weight: 700; letter-spacing: -0.5px; color: #E0E0E0; }
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 95%; }
</style>
""", unsafe_allow_html=True)

# --- 2. LOAD V3 MODEL ---
@st.cache_resource
def load_ml_model():
    if os.path.exists("traffic_model.pkl"):
        return joblib.load("traffic_model.pkl")
    return None

ai_model = load_ml_model()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# --- 3. SIDEBAR: THE SENSOR INPUTS ---
st.sidebar.header("🚦 Route Telemetry")
st.sidebar.markdown("Input route parameters to query the V3 XGBoost Engine.")

target_road = st.sidebar.selectbox("Select Route:", ["mwenge", "ubungo", "selander", "tazara", "sam_nujoma", "kilwa_mbagala", "posta_to_tegeta"])
sim_date = st.sidebar.date_input("Simulation Date", datetime.today())
sim_time = st.sidebar.time_input("Simulation Time", datetime.now().time())
sim_temp = st.sidebar.slider("Temperature (°C)", 20.0, 35.0, 25.0)
sim_rain = st.sidebar.toggle("Heavy Rain / Flooding", False)

# This mimics the "Velocity" feature without making the user do math
traffic_trend = st.sidebar.selectbox("Current Traffic Trend", ["Stable", "Getting Worse (Building)", "Clearing Up"])
velocity_map = {"Stable": 0.0, "Getting Worse (Building)": 10.0, "Clearing Up": -10.0}
sim_velocity = velocity_map[traffic_trend]

# --- 4. XGBOOST CALCULATION & XAI ---
st.title("🤖 DarTraffic AI Oracle")

if ai_model:
    # Feature Engineering (The Translation Layer)
    dt = datetime.combine(sim_date, sim_time)
    hour = dt.hour
    day_of_week = dt.weekday()
    is_weekend = 1 if day_of_week >= 5 else 0
    is_rush_hour = 1 if hour in [7, 8, 16, 17, 18, 19] else 0
    is_raining = 1 if sim_rain else 0

    input_data = pd.DataFrame([{
        "road_id": target_road, "hour": hour, "day_of_week": day_of_week,
        "is_weekend": is_weekend, "is_rush_hour": is_rush_hour,
        "temp_c": sim_temp, "is_raining": is_raining, "delay_velocity": sim_velocity
    }])

    prediction = float(ai_model.predict(input_data)[0])
    predicted_delay = max(0.0, round(prediction, 1))

    # XAI (Explainable AI) Generation
    reasoning = []
    if is_rush_hour: reasoning.append("Peak Rush Hour")
    if is_raining: reasoning.append("Adverse Weather (Rain)")
    if sim_velocity > 0: reasoning.append("Rapidly Compounding Velocity")
    
    explanation = "Traffic is flowing optimally."
    if predicted_delay > 15:
        factors = " + ".join(reasoning) if reasoning else "Heavy localized congestion"
        explanation = f"🔴 Gridlock predicted due to: **{factors}**."
    elif predicted_delay > 5:
        explanation = "🟡 Moderate friction expected."

    # UI Metrics Display
    col1, col2, col3 = st.columns(3)
    col1.metric("Predicted Clearing Time", f"{predicted_delay} mins", f"± 3.0 min confidence")
    col2.metric("Flow Status", "Gridlock" if predicted_delay > 15 else "Moderate" if predicted_delay > 5 else "Clear")
    col3.info(explanation)
    
    st.divider()

    # --- 5. GEMINI COPILOT (Context-Aware) ---
    st.subheader("💬 AI Copilot Advisory")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask for routing advice (e.g., 'Should I leave now or wait?')"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            
            # Injecting the XGBoost exact math into the LLM
            context_injection = f"The user is asking about {target_road}. The exact calculated ETA from the XGBoost ML model is {predicted_delay} minutes. {explanation}"
            
            system_prompt = f"""
            You are 'FlowTrack Copilot', an elite logistics AI in Dar es Salaam.
            [XGBOOST SENSOR DATA]: {context_injection}
            
            [STRICT DIRECTIVES]
            1. NEVER say you can't predict the future. You have the exact ETA in the sensor data.
            2. Base your routing advice explicitly on the provided XGBoost ETA.
            3. Keep answers concise, authoritative, and actionable. Do not use markdown headers.
            """

            try:
                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content(system_prompt + "\n\nUser Question: " + prompt)
                
                message_placeholder.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                message_placeholder.error(f"LLM Connection Error: {e}")
else:
    st.error("⚠️ AI Brain (traffic_model.pkl) not found in directory. Train model first.")
