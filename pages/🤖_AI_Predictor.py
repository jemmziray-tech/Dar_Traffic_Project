import os
import pandas as pd
from datetime import datetime
import pytz
import plotly.express as px
import streamlit as st
import joblib
import google.generativeai as genai
from dotenv import load_dotenv

# --- Load Environment Variables securely ---
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
        # 1. Convert Time to Decimal for Model (e.g., 08:30 -> 8.5)
        h, m = map(int, target_time_str.split(":"))
        target_fraction = h + (m / 60.0)

        # 2. Make Exact Prediction
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

        # 3. Dynamic Confidence Score fetching
        confidence_score = "Active"
        try:
            if os.path.exists("model_metrics.csv"):
                metrics_df = pd.read_csv("model_metrics.csv")
                latest_r2 = metrics_df.iloc[-1]["R2_Score"]
                if pd.notna(latest_r2):
                    confidence_score = f"{latest_r2 * 100:.1f}% R²"
        except Exception:
            pass

        # 4. Result Metrics
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

        # 5. Generate the Time-Curve with NUMERIC Data
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

        # Helper to create formatted hover strings
        def format_frac(f):
            hr, mn = int(f), int(round((f - int(f)) * 60))
            return f"{hr:02d}:{mn:02d}"

        curve_df["Time_Label"] = curve_df["Hour"].apply(format_frac)

        # 6. Build the mathematically safe Plotly chart
        st.markdown("**Departure Window Analysis**")
        fig = px.area(
            curve_df,
            x="Hour",
            y="Predicted_Delay",
            hover_data={"Time_Label": True, "Hour": False},
            template="plotly_dark",
            height=250,
        )

        fig.update_traces(line_color="#4B8BBE", fillcolor="rgba(75, 139, 190, 0.2)")

        # Add a vertical line using the decimal number, NOT the string
        fig.add_vline(
            x=target_fraction,
            line_width=2,
            line_dash="dash",
            line_color="#ffc107",
            annotation_text="Your Trip",
            annotation_position="top right",
        )

        # Format the X-axis to display strings instead of decimals
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
            "Predictive Model Offline: traffic_model.pkl not found in root directory.",
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
                        "content": "Hello! I am your data-driven AI Traffic Assistant. Ask me about alternative routes for your planned trip.",
                    }
                ]

            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            if prompt := st.chat_input("E.g., Can I shift to Mandela Rd instead?"):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    message_placeholder = st.empty()

                    # 🚨 THE HACKATHON WINNER: THE SHADOW INTELLIGENCE FEED
                    context_injection = ""
                    if rf_model:
                        # 1. Instantly predict the traffic for ALL 21 roads at the selected time
                        all_roads = list(REVERSE_ROAD_MAP.values())
                        city_df = pd.DataFrame(
                            {
                                "road_id": all_roads,
                                "Hour": [target_fraction] * len(all_roads),
                                "Day": [target_day] * len(all_roads),
                                "Condition": [target_weather] * len(all_roads),
                            }
                        )
                        city_df["Predicted_Delay"] = rf_model.predict(city_df)

                        # 2. Format it into a clean data feed for the AI
                        city_status = ""
                        for _, row in city_df.iterrows():
                            friendly_name = ROAD_MAP[row["road_id"]]
                            city_status += f"- {friendly_name}: {row['Predicted_Delay']:.1f} mins\n"

                        # 3. Inject it into the AI's brain
                        context_injection = f"""
                        [SYSTEM DATA FEED]
                        The user is evaluating a departure on {target_day} at {target_time_str} under {target_weather} conditions.
                        Their Primary Route: '{target_road_name}' (Predicted Delay: {exact_prediction:.1f} mins).

                        CITY-WIDE PREDICTIVE TELEMETRY FOR THIS EXACT TIME:
                        {city_status}
                        """

                    system_prompt = f"""
                    You are 'DarTraffic Copilot', an elite, data-driven logistics AI.
                    {context_injection}
                    
                    [STRICT DIRECTIVES]
                    1. NEVER give generic, memorized advice (e.g., "Mandela road is usually busy"). 
                    2. If the user asks about an alternative road, you MUST look at the telemetry feed above and quote the EXACT predicted minutes for that alternative road.
                    3. Compare the alternative directly to their Primary Route to tell them mathematically if it's a faster choice.
                    4. Keep your answer concise, corporate, and highly analytical. Maximum 3 to 4 sentences.
                    """

                    try:
                        model = genai.GenerativeModel("gemini-2.5-flash")
                        full_prompt = system_prompt + "\n\nUser Question: " + prompt
                        response = model.generate_content(full_prompt)

                        message_placeholder.markdown(response.text)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": response.text}
                        )
                    except Exception as e:
                        message_placeholder.error(f"Connection Error: {e}")
