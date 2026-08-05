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

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, [class*="css"], .stApp { font-family: 'Inter', sans-serif !important; background-color: #0A0F1E; color: #E8EAF0; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0D1426 0%, #0A0F1E 100%) !important; border-right: 1px solid rgba(0,212,255,0.1); }
.block-container { padding-top: 1.8rem; padding-bottom: 2rem; max-width: 98%; }
div[data-testid="stMetricValue"] { font-weight: 700; font-size: 1.5rem !important; letter-spacing: -0.5px; color: #FFFFFF; }
div[data-testid="stMetricLabel"] { color: #8892A4 !important; font-size: 0.75rem; font-weight: 500; letter-spacing: 0.5px; text-transform: uppercase; }
[data-testid="stMetricDelta"] { font-weight: 600; }
.stChatInput { padding-bottom: 20px; }
.page-header { font-size: 1.8rem; font-weight: 800; color: #FFFFFF; letter-spacing: -0.8px; }
.page-sub { font-size: 0.85rem; color: #5C6680; margin-top: 4px; }
.pred-result-card {
    background: rgba(0,212,255,0.04);
    border: 1px solid rgba(0,212,255,0.2);
    border-radius: 14px;
    padding: 24px;
    text-align: center;
    margin-top: 16px;
}
.pred-delay-value { font-size: 3.5rem; font-weight: 800; color: #FFFFFF; letter-spacing: -2px; line-height: 1; }
.pred-delay-unit { font-size: 1rem; font-weight: 400; color: #8892A4; }
.pred-status-badge {
    display: inline-block; padding: 4px 14px;
    border-radius: 20px; font-size: 0.8rem; font-weight: 700;
    letter-spacing: 1px; text-transform: uppercase; margin-top: 12px;
}
.pred-smooth { background: rgba(46,213,115,0.12); color: #2ED573; border: 1px solid rgba(46,213,115,0.3); }
.pred-moderate { background: rgba(255,165,2,0.12); color: #FFA502; border: 1px solid rgba(255,165,2,0.3); }
.pred-jammed { background: rgba(255,71,87,0.12); color: #FF4757; border: 1px solid rgba(255,71,87,0.3); }
.confidence-label { font-size: 0.75rem; color: #5C6680; margin-top: 10px; }
.section-label { font-size: 0.7rem; font-weight: 600; color: #00D4FF; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 12px; }
.stButton > button { border-radius: 8px !important; font-weight: 600 !important; font-family: 'Inter', sans-serif !important; }
.stButton > button[kind="primary"] { background: linear-gradient(135deg, #00D4FF, #0099CC) !important; border: none !important; color: #0A0F1E !important; }
</style>
""", unsafe_allow_html=True)



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

DAYS_MAP = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}


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
st.title(":material/explore: AI Commute Predictor & Copilot")
st.caption(
    "Plan your journey using our XGBoost prediction engine and consult the Gemini AI Copilot for logistics advice."
)
st.divider()

# --- 5. ASYMMETRIC DASHBOARD LAYOUT (60/40) ---
col_ml, col_chat = st.columns([1.5, 1], gap="large")

# =========================================================
# LEFT COLUMN (60%): DETERMINISTIC ROUTING ENGINE
# =========================================================
with col_ml:
    st.subheader(":material/fork_right: Trip Parameters")

    # Input Form
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
        # A. Mathematics & Prediction
        h, m = map(int, target_time_str.split(":"))
        target_fraction = h + (m / 60.0)  # Converts 08:30 to 8.5

        pred_df = build_features_df(target_road_id, target_day, target_fraction, target_weather)
        exact_prediction = float(rf_model.predict(pred_df)[0])
        exact_prediction = max(0.0, round(exact_prediction, 1))

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
        st.subheader(":material/flag: Predicted Outcome")
        m1, m2 = st.columns(2)
        m1.metric(
            "Estimated Delay",
            f"{exact_prediction:.1f} Mins",
            delta=status_text,
            delta_color=pred_color,
        )
        m2.metric(
            "Confidence Score",
            confidence_score,
            delta="Validated against historicals",
            delta_color="normal",
        )

        # D. Time-Shift Curve Generation
        start_frac = max(6.0, target_fraction - 1.5)
        end_frac = min(23.75, target_fraction + 1.5)
        curve_hours = [
            start_frac + (i * 0.25)
            for i in range(int((end_frac - start_frac) / 0.25) + 1)
        ]

        curve_rows = []
        for h_frac in curve_hours:
            f_row = build_features_df(target_road_id, target_day, h_frac, target_weather)
            f_row["Hour"] = h_frac
            curve_rows.append(f_row)
        curve_df = pd.concat(curve_rows, ignore_index=True)
        curve_df["Predicted_Delay"] = [max(0.0, float(val)) for val in rf_model.predict(curve_df.drop(columns=["Hour"]))]

        def format_frac(f):
            hr, mn = int(f), int(round((f - int(f)) * 60))
            return f"{hr:02d}:{mn:02d}"

        curve_df["Time_Label"] = curve_df["Hour"].apply(format_frac)

        # E. Beautiful Plotly Area Chart (Mathematically Safe)
        st.markdown("**Departure Window Analysis**")
        fig = px.area(
            curve_df,
            x="Hour",
            y="Predicted_Delay",
            hover_data={"Time_Label": True, "Hour": False},
            template="plotly_dark",
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
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis_title="",
            yaxis_title="Minutes Delayed",
            xaxis=dict(
                showgrid=False,
                tickmode="array",
                tickvals=curve_df["Hour"].tolist(),
                ticktext=curve_df["Time_Label"].tolist(),
            ),
            yaxis=dict(showgrid=True, gridcolor="#333333"),
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.error(
            "Predictive Model Offline: traffic_model.pkl not found.",
            icon=":material/warning:",
        )


# =========================================================
# RIGHT COLUMN (40%): DARTRAFFIC COPILOT (GEMINI 2.5)
# =========================================================
with col_chat:
    st.subheader(":material/robot_2: DarTraffic Copilot")
    st.caption("Ask our AI about alternatives, wait times, or strategy.")

    with st.container(border=True, height=530):
        if not genai_active:
            st.info(
                "Configure GEMINI_API_KEY in environment to activate Copilot.",
                icon=":material/key:",
            )
        else:
            # Initialize Chat Memory
            if "messages" not in st.session_state:
                st.session_state.messages = [
                    {
                        "role": "assistant",
                        "content": "Hello! I am your AI Logistics Assistant. Ask me if you should reroute or delay your departure.",
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
                        # 1. SPATIAL MATRIX: All roads at the exact selected time
                        all_roads = list(REVERSE_ROAD_MAP.values())
                        city_df = build_features_df(all_roads, target_day, target_fraction, target_weather)
                        city_df["Predicted_Delay"] = [max(0.0, float(val)) for val in rf_model.predict(city_df)]

                        city_status = ""
                        for idx, row in city_df.iterrows():
                            friendly_name = ROAD_MAP[row["road_id"]]
                            city_status += f"- {friendly_name}: {row['Predicted_Delay']:.1f} mins\n"

                        # 2. TEMPORAL MATRIX: The user's target road over a 3-hour window
                        time_trend = ""
                        if "curve_df" in locals():
                            for _, row in curve_df.iterrows():
                                time_trend += f"- {row['Time_Label']}: {row['Predicted_Delay']:.1f} mins\n"

                        # 3. Injecting the Brain
                        context_injection = f"""
                        [SYSTEM DATA FEED]
                        The user is evaluating a departure on {target_day} at {target_time_str} under {target_weather} conditions.
                        Their Primary Route: '{target_road_name}' (Predicted Delay: {exact_prediction:.1f} mins).

                        1. CITY-WIDE ALTERNATIVES (At exactly {target_time_str}):
                        {city_status}

                        2. TIME-SHIFT PREDICTIONS FOR PRIMARY ROUTE ('{target_road_name}'):
                        {time_trend}
                        """

                    system_prompt = f"""
                    You are 'DarTraffic Copilot', an elite, data-driven logistics AI.
                    {context_injection}
                    
                    [STRICT DIRECTIVES]
                    1. NEVER claim you cannot predict the future. You have the exact predictive time-shift data in the feed above.
                    2. If the user asks about shifting to another road, use the CITY-WIDE ALTERNATIVES feed to compare delays mathematically.
                    3. If the user asks if they should "wait" or "leave later", use the TIME-SHIFT PREDICTIONS feed. Tell them exactly what the delay will be at the specific times in the feed.
                    4. Keep your answer concise, corporate, and highly analytical. Maximum 3 to 4 sentences.
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

