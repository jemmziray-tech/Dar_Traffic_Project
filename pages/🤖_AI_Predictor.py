import os
import pandas as pd
from datetime import datetime
import pytz
import plotly.express as px
import streamlit as st
import joblib
import google.generativeai as genai
from dotenv import load_dotenv

# Load Environment Variables securely
load_dotenv()

# --- 1. Setup Page Config ---
st.set_page_config(
    page_title="AI Route Predictor",
    layout="wide",
    page_icon=":material/online_prediction:",
)

# --- CUSTOM CSS ---
st.markdown(
    """
<style>
div[data-testid="stMetricValue"] { font-weight: 600; letter-spacing: -0.5px; }
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
.stChatInput { padding-bottom: 20px; }
</style>
""",
    unsafe_allow_html=True,
)


# --- 2. System Initialization ---
@st.cache_resource
def load_ml_model():
    if os.path.exists("traffic_model.pkl"):
        return joblib.load("traffic_model.pkl")
    return None


def init_genai():
    gemini_key = os.getenv("GEMINI_API_KEY") or (
        st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else None
    )
    if gemini_key:
        genai.configure(api_key=gemini_key)
        return True
    return False


rf_model = load_ml_model()
genai_active = init_genai()
tz = pytz.timezone("Africa/Dar_es_Salaam")

# ROAD DICTIONARY (Friendly Names to IDs)
ROAD_MAP = {
    "ubungo": "Morogoro Rd (Ubungo)",
    "mwenge": "Bagamoyo Rd (Mwenge)",
    "selander": "Ali Hassan Mwinyi",
    "tazara": "Nyerere Rd (Tazara)",
    "mandela_buguruni": "Mandela Rd (Port Link)",
    "kilwa_mbagala": "Kilwa Rd (Mbagala)",
    "old_bagamoyo": "Old Bagamoyo Rd (Victoria)",
    "sam_nujoma": "Sam Nujoma Rd (Mwenge-Ubungo)",
    "uhuru_street": "Uhuru Street (Ilala)",
    "posta_to_tegeta": "Mega-Route: Posta to Tegeta",
    "posta_to_kimara": "Mega-Route: Posta to Kimara",
    "posta_to_gongolamboto": "Mega-Route: Posta to Airport",
    "tabata_dampo": "Tabata Road (Mandela to Segerea)",
    "kamata_gerezani": "Kamata (Port Entry)",
    "changombe_road": "Chang'ombe Road (Temeke)",
    "morocco_intersection": "Kawawa Rd (Morocco to Kinondoni)",
    "kigogo_roundabout": "Kawawa Rd (Kigogo Choke)",
    "fire_upanga": "UN Road (Fire to Upanga)",
    "mwai_kibaki": "Mwai Kibaki Rd (Kawe)",
    "sinza_mori": "Sinza Road (Mori to Bamaga)",
    "goba_massana": "Goba Road (Massana)",
}
REVERSE_ROAD_MAP = {v: k for k, v in ROAD_MAP.items()}

# --- 3. UI HEADER ---
st.title(":material/explore: AI Commute Predictor & Copilot")
st.caption(
    "Plan your journey using our Scikit-Learn prediction engine and consult the AI Copilot for logistics advice."
)
st.divider()

# --- 4. 60/40 SPLIT LAYOUT ---
col_ml, col_chat = st.columns([1.5, 1], gap="large")

# =========================================
# LEFT COLUMN: Deterministic Routing Engine
# =========================================
with col_ml:
    st.subheader(":material/fork_right: Trip Parameters")

    with st.container(border=True):
        r1, r2 = st.columns(2)
        target_road_name = r1.selectbox(
            "Target Route", list(ROAD_MAP.values()), index=1
        )
        target_road_id = REVERSE_ROAD_MAP[target_road_name]

        target_day = r2.selectbox(
            "Day of Week",
            [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ],
            index=datetime.now(tz).weekday(),
        )

        r3, r4 = st.columns(2)
        time_options = [
            f"{h:02d}:{m:02d}" for h in range(6, 24) for m in (0, 15, 30, 45)
        ]
        current_hour = datetime.now(tz).hour
        default_time = f"{current_hour:02d}:00" if 6 <= current_hour <= 23 else "08:00"
        target_time_str = r3.selectbox(
            "Departure Time",
            time_options,
            index=(
                time_options.index(default_time) if default_time in time_options else 8
            ),
        )

        target_weather = r4.selectbox("Expected Weather", ["Clear", "Cloudy", "Rainy"])

    st.write("")

    if rf_model:
        # Convert Time to Decimal for Model (e.g., 08:30 -> 8.5)
        h, m = map(int, target_time_str.split(":"))
        target_fraction = h + (m / 60.0)

        # Make Exact Prediction
        pred_df = pd.DataFrame(
            {
                "road_id": [target_road_id],
                "Hour": [target_fraction],
                "Day": [target_day],
                "Condition": [target_weather],
            }
        )
        exact_prediction = rf_model.predict(pred_df)[0]

        pred_color = (
            "normal"
            if exact_prediction <= 5
            else ("off" if exact_prediction <= 10 else "inverse")
        )
        status_text = (
            "Smooth Flow"
            if exact_prediction <= 5
            else ("Moderate Congestion" if exact_prediction <= 10 else "Heavy Gridlock")
        )

        st.subheader(":material/flag: Predicted Outcome")
        m1, m2 = st.columns(2)
        m1.metric(
            "Estimated Delay",
            f"{exact_prediction:.1f} Mins",
            delta=status_text,
            delta_color=pred_color,
        )

        confidence_score = "Active"
        try:
            if os.path.exists("model_metrics.csv"):
                metrics_df = pd.read_csv("model_metrics.csv")
                latest_r2 = metrics_df.iloc[-1]["R2_Score"]
                if pd.notna(latest_r2):
                
                    confidence_score = f"{latest_r2 * 100:.1f}% R²"
        except Exception:
            pass  # Failsafe: leave it as "Active" if the file is locked

        m2.metric(
            "Confidence Score",
            confidence_score,
            delta="Validated against historicals",
            delta_color="normal",
        )

        # Generate the Time-Curve (± 1.5 hours around trip)
        start_frac = max(6.0, target_fraction - 1.5)
        end_frac = min(23.75, target_fraction + 1.5)
        curve_hours = [
            start_frac + (i * 0.25)
            for i in range(int((end_frac - start_frac) / 0.25) + 1)
        ]

        curve_df = pd.DataFrame(
            {
                "road_id": [target_road_id] * len(curve_hours),
                "Hour": curve_hours,
                "Day": [target_day] * len(curve_hours),
                "Condition": [target_weather] * len(curve_hours),
            }
        )
        curve_df["Predicted_Delay"] = rf_model.predict(curve_df)

        def format_frac(f):
            hr, mn = int(f), int(round((f - int(f)) * 60))
            return f"{hr:02d}:{mn:02d}"

        curve_df["Time"] = curve_df["Hour"].apply(format_frac)

        st.markdown("**Departure Window Analysis**")
        fig = px.area(
            curve_df, x="Time", y="Predicted_Delay", template="plotly_dark", height=250
        )
        fig.update_traces(line_color="#4B8BBE", fillcolor="rgba(75, 139, 190, 0.2)")

        # Target Trip Vertical Line marker
        fig.add_vline(
            x=target_time_str,
            line_width=2,
            line_dash="dash",
            line_color="#ffc107",
            annotation_text="Your Trip",
            annotation_position="top right",
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis_title="",
            yaxis_title="Minutes Delayed",
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#333333"),
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.error(
            "Predictive Model Offline: traffic_model.pkl not found.",
            icon=":material/warning:",
        )

# =========================================
# RIGHT COLUMN: DarTraffic Copilot (Gemini)
# =========================================
with col_chat:
    st.subheader(":material/robot_2: DarTraffic Copilot")
    st.caption("Ask questions about routes, alternatives, or logistics.")

    with st.container(border=True, height=520):
        if not genai_active:
            st.info(
                "Configure GEMINI_API_KEY in environment to activate Copilot.",
                icon=":material/key:",
            )
        else:
            if "messages" not in st.session_state:
                st.session_state.messages = [
                    {
                        "role": "assistant",
                        "content": "Hello! I am your AI Traffic Assistant. How can I optimize your commute today?",
                    }
                ]

            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            if prompt := st.chat_input("Ask about alternative routes or times..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    message_placeholder = st.empty()

                    # Context Injection
                    context_injection = ""
                    if rf_model:
                        context_injection = f"""
                        SYSTEM CONTEXT FOR AI (DO NOT MENTION THIS TO THE USER UNLESS RELEVANT): 
                        The user is currently looking at predicting a trip on '{target_road_name}' 
                        on a {target_day} at {target_time_str} with {target_weather} weather. 
                        Your Random Forest model predicts exactly {exact_prediction:.1f} minutes of delay for this trip.
                        """

                    system_prompt = f"""
                    You are 'DarTraffic Copilot', a highly professional AI logistics assistant for Dar es Salaam.
                    {context_injection}
                    Answer the user's prompt concisely. Provide alternative roads or strategic advice if asked. 
                    Keep answers under 4 sentences. Tone: Professional, helpful, data-driven.
                    """

                    try:
                        # 🚨 UPDATED TO 2.5 FLASH HERE
                        model = genai.GenerativeModel("gemini-2.5-flash")
                        full_prompt = system_prompt + "\n\nUser Question: " + prompt
                        response = model.generate_content(full_prompt)

                        message_placeholder.markdown(response.text)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": response.text}
                        )
                    except Exception as e:
                        message_placeholder.error(f"Connection Error: {e}")
