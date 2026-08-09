import os
import pandas as pd
from datetime import datetime
import pytz
import plotly.express as px
import streamlit as st
import joblib
import google.generativeai as genai
from dotenv import load_dotenv

# --- 0. SECURE ENVIRONMENT INITIALIZATION ---
load_dotenv()

# --- 1. PAGE CONFIGURATION & CSS ---
st.set_page_config(
    page_title="AI Route Predictor",
    layout="wide",
    page_icon=":material/online_prediction:",
)

# --- 2. CORE SYSTEM INITIALIZATION ---
@st.cache_resource
def load_ml_model():
    """Loads the Scikit-Learn model from disk, cached for performance."""
    if os.path.exists("traffic_model.pkl"):
        return joblib.load("traffic_model.pkl")
    return None


def init_genai():
    """Initializes Gemini AI using secure environment variables."""
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

# --- 3. MASTER ROAD DICTIONARY ---
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import ROAD_MAP, REVERSE_ROAD_MAP, ROUTES

DAYS_MAP = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
ORIGINS = sorted(list(set(o for o, _ in ROUTES.keys())))


def build_features_df(road_ids, target_day, hour_fraction, target_weather):
    r_list = road_ids if isinstance(road_ids, list) else [road_ids]
    day_idx = DAYS_MAP.get(target_day, 0)
    is_wkd = 1 if day_idx >= 5 else 0
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
            for r_id in r_list
        ]
    )


# --- 4. HEADER UI ---
st.title("🤖 AI Commute Predictor & Mshauri")
st.caption(
    "Plan your journey using our XGBoost prediction engine and consult Mshauri (AI Copilot) for logistics advice."
)
st.divider()

# --- 5. ASYMMETRIC DASHBOARD LAYOUT (60/40) ---
col_ml, col_chat = st.columns([1.5, 1], gap="large")

# =========================================================
# LEFT COLUMN (60%): DETERMINISTIC ROUTING ENGINE
# =========================================================
with col_ml:
    st.subheader("🛣️ Trip Parameters")

    # Input Form
    with st.container(border=True):
        r1, r2, r3 = st.columns([1.5, 1.5, 2])
        origin = r1.selectbox("Origin", ORIGINS, key="ai_origin")
        valid_destinations = sorted(list(set(d for o, d in ROUTES.keys() if o == origin)))
        destination = r2.selectbox("Destination", valid_destinations, key="ai_dest")
        
        route_options = ROUTES.get((origin, destination), {})
        route_names = list(route_options.keys())
        target_route_name = r3.selectbox("Route Option", route_names, key="ai_route")
        
        # Get the segments for the selected route
        target_road_ids = route_options[target_route_name]

        r_day, r_time, r_weather = st.columns(3)
        target_day = r_day.selectbox(
            "Day of Week",
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            index=datetime.now(tz).weekday(),
        )

        time_options = [f"{h:02d}:{m:02d}" for h in range(6, 24) for m in (0, 15, 30, 45)]
        current_hour = datetime.now(tz).hour
        default_time = f"{current_hour:02d}:00" if 6 <= current_hour <= 23 else "08:00"
        target_time_str = r_time.selectbox(
            "Departure Time",
            time_options,
            index=(time_options.index(default_time) if default_time in time_options else 8),
        )

        target_weather = r_weather.selectbox("Expected Weather", ["Clear", "Cloudy", "Rainy"])

    st.write("")

    if rf_model:
        # A. Mathematics & Prediction
        h, m = map(int, target_time_str.split(":"))
        target_fraction = h + (m / 60.0)  # Converts 08:30 to 8.5

        # Predict delays for ALL segments in the selected route
        pred_df = build_features_df(target_road_ids, target_day, target_fraction, target_weather)
        segment_predictions = [max(0.0, float(val)) for val in rf_model.predict(pred_df)]
        exact_prediction = round(sum(segment_predictions), 1)

        pred_color = (
            "normal"
            if exact_prediction <= 10
            else ("off" if exact_prediction <= 25 else "inverse")
        )
        status_text = (
            "Smooth Flow"
            if exact_prediction <= 10
            else ("Moderate Congestion" if exact_prediction <= 25 else "Heavy Gridlock")
        )

        # B. Dynamic Confidence Score
        confidence_score = "Active"
        try:
            if os.path.exists("model_metrics.csv"):
                metrics_df = pd.read_csv("model_metrics.csv")
                latest_r2 = metrics_df.iloc[-1]["R2_Score"]
                if pd.notna(latest_r2):
                    confidence_score = f"{latest_r2 * 100:.1f}% R²"
        except Exception:
            pass  # Fail gracefully, ensuring the app never crashes

        # C. Metric Display
        st.subheader("🎯 Predicted Outcome")
        m1, m2 = st.columns(2)
        with m1:
            with st.container(border=True):
                st.metric(
                    "Estimated Extra Delay",
                    f"{exact_prediction:.1f} Mins",
                    delta=status_text,
                    delta_color=pred_color,
                )
        with m2:
            with st.container(border=True):
                st.metric(
                    "Confidence Score",
                    confidence_score,
                    delta="Validated against historicals",
                    delta_color="normal",
                )

        # D. Time-Shift Curve Generation (Predicting the entire route over time)
        start_frac = max(6.0, target_fraction - 1.5)
        end_frac = min(23.75, target_fraction + 1.5)
        curve_hours = [start_frac + (i * 0.25) for i in range(int((end_frac - start_frac) / 0.25) + 1)]

        curve_rows = []
        for h_frac in curve_hours:
            f_row = build_features_df(target_road_ids, target_day, h_frac, target_weather)
            f_row["Hour"] = h_frac
            curve_rows.append(f_row)
        
        curve_df = pd.concat(curve_rows, ignore_index=True)
        # Predict all segments for all time slices at once
        predictions = rf_model.predict(curve_df.drop(columns=["Hour"]))
        curve_df["Predicted_Delay"] = [max(0.0, float(val)) for val in predictions]
        
        # Group by hour and sum the delays across all segments for that hour
        route_curve = curve_df.groupby("Hour")["Predicted_Delay"].sum().reset_index()

        def format_frac(f):
            hr, mn = int(f), int(round((f - int(f)) * 60))
            return f"{hr:02d}:{mn:02d}"

        route_curve["Time_Label"] = route_curve["Hour"].apply(format_frac)

        # E. Beautiful Plotly Area Chart (Mathematically Safe)
        st.markdown("**Departure Window Analysis**")
        fig = px.area(
            route_curve,
            x="Hour",
            y="Predicted_Delay",
            hover_data={"Time_Label": True, "Hour": False},
            height=260,
        )

        fig.update_traces(line_color="#4B8BBE", fillcolor="rgba(75, 139, 190, 0.25)")
        fig.add_vline(
            x=target_fraction,
            line_width=2,
            line_dash="dash",
            line_color="#ffc107",
            annotation_text="Your Trip",
            annotation_position="top right",
        )

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#8892A4"),
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis_title="",
            yaxis_title="Total Mins Delayed",
            xaxis=dict(
                showgrid=False,
                tickmode="array",
                tickvals=route_curve["Hour"].tolist(),
                ticktext=route_curve["Time_Label"].tolist(),
            ),
            yaxis=dict(showgrid=True, gridcolor="#333333"),
        )
        st.plotly_chart(fig, use_container_width=True, theme="streamlit")

    else:
        st.error(
            "Predictive Model Offline: traffic_model.pkl not found.",
            icon="⚠️",
        )


# =========================================================
# RIGHT COLUMN (40%): DARTRAFFIC COPILOT (MSHAURI)
# =========================================================
with col_chat:
    st.subheader("💬 Mshauri")
    st.caption("Ask our AI about alternatives, wait times, or strategy.")

    with st.container(border=True, height=530):
        if not genai_active:
            st.info(
                "Configure GEMINI_API_KEY in environment to activate Mshauri.",
                icon="🔑",
            )
        else:
            # Initialize Chat Memory
            if "messages" not in st.session_state:
                st.session_state.messages = [
                    {
                        "role": "assistant",
                        "content": "Habari! I am Mshauri, your AI Logistics Advisor. Ask me if you should reroute or delay your departure.",
                    }
                ]

            # Render Chat History
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # Input Prompt
            if prompt := st.chat_input("E.g., Should I wait an hour or go now?"):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    message_placeholder = st.empty()

                    context_injection = ""
                    if rf_model:
                        # 1. SPATIAL MATRIX: Calculate total delay for all alternative routes
                        alt_routes_status = ""
                        for r_name, r_segments in route_options.items():
                            if r_name != target_route_name:
                                alt_df = build_features_df(r_segments, target_day, target_fraction, target_weather)
                                alt_preds = [max(0.0, float(val)) for val in rf_model.predict(alt_df)]
                                alt_total = sum(alt_preds)
                                alt_routes_status += f"- {r_name}: {alt_total:.1f} mins extra delay\n"
                        
                        if not alt_routes_status:
                            alt_routes_status = "No alternative routes configured for this Origin-Destination pair.\n"

                        # 2. TEMPORAL MATRIX: The user's target route over a 3-hour window
                        time_trend = ""
                        if "route_curve" in locals():
                            for _, row in route_curve.iterrows():
                                time_trend += f"- {row['Time_Label']}: {row['Predicted_Delay']:.1f} mins extra delay\n"

                        # 3. Injecting the Brain
                        context_injection = f"""
                        [SYSTEM DATA FEED]
                        The user is evaluating a departure from {origin} to {destination} on {target_day} at {target_time_str} under {target_weather} conditions.
                        Their Selected Route: '{target_route_name}' (Predicted Extra Delay: {exact_prediction:.1f} mins).

                        1. ALTERNATIVE ROUTES (At exactly {target_time_str}):
                        {alt_routes_status}

                        2. TIME-SHIFT PREDICTIONS FOR SELECTED ROUTE ('{target_route_name}'):
                        {time_trend}
                        """

                    system_prompt = f"""
                    You are 'Mshauri', an elite, data-driven logistics AI advisor for Dar es Salaam.
                    {context_injection}
                    
                    [STRICT DIRECTIVES]
                    1. NEVER claim you cannot predict the future. You have the exact predictive time-shift data in the feed above.
                    2. If the user asks about shifting to another route, use the ALTERNATIVE ROUTES feed to compare delays mathematically.
                    3. If the user asks if they should "wait" or "leave later", use the TIME-SHIFT PREDICTIONS feed. Tell them exactly what the delay will be at the specific times in the feed.
                    4. Keep your answer concise, highly analytical, and friendly. Maximum 3 to 4 sentences.
                    """

                    try:
                        # Powered by Gemini 2.0 Flash
                        model = genai.GenerativeModel("gemini-2.0-flash")
                        full_prompt = system_prompt + "\n\nUser Question: " + prompt
                        response = model.generate_content(full_prompt)

                        message_placeholder.markdown(response.text)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": response.text}
                        )
                    except Exception as e:
                        message_placeholder.error(f"Connection Error: {e}")
