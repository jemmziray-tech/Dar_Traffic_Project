import os
import json
import time
from datetime import datetime
import pytz
import pandas as pd
import pydeck as pdk
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import joblib
import plotly.express as px
import google.generativeai as genai

# --- 1. Setup Page Config ---
st.set_page_config(
    page_title="Dar Traffic Intelligence",
    layout="wide",
    page_icon=":material/satellite_alt:",
)

# --- CUSTOM CSS (Minimalist & Sleek) ---
st.markdown(
    """
<style>
.blob { border-radius: 50%; margin-right: 12px; height: 14px; width: 14px; transform: scale(1); }
.blob.green { background: rgba(40, 167, 69, 1); box-shadow: 0 0 8px rgba(40, 167, 69, 0.5); }
.blob.yellow { background: rgba(255, 193, 7, 1); box-shadow: 0 0 8px rgba(255, 193, 7, 0.5); }
.blob.red { background: rgba(220, 53, 69, 1); box-shadow: 0 0 8px rgba(220, 53, 69, 0.5); }
.block-container { padding-top: 2rem; padding-bottom: 2rem; }
/* Dark theme adjustments for cleaner look */
div[data-testid="stMetricValue"] { font-weight: 600; letter-spacing: -0.5px; }
</style>
""",
    unsafe_allow_html=True,
)

# --- 2. Connect to Firebase (Enterprise Auth) ---
if not firebase_admin._apps:
    try:
        if os.path.exists("firebase-key.json"):
            cred = credentials.Certificate("firebase-key.json")
        elif "firebase" in st.secrets:
            if "key_data" in st.secrets["firebase"]:
                key_dict = json.loads(st.secrets["firebase"]["key_data"])
                cred = credentials.Certificate(key_dict)
            else:
                firebase_secrets = dict(st.secrets["firebase"])
                cred = credentials.Certificate(firebase_secrets)
        else:
            st.error(
                "Authentication Failure: No valid Firebase credentials detected.",
                icon=":material/lock_open_right:",
            )
            st.stop()
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Telemetry Connection Error: {e}", icon=":material/cell_tower:")
        st.stop()

db = firestore.client()

# --- 3. MASTER CITY GRID COORDINATES (21 Routes) ---
ROAD_COORDS = {
    "ubungo": {"lat": -6.8009, "lon": 39.2250},
    "mwenge": {"lat": -6.7687, "lon": 39.2460},
    "selander": {"lat": -6.8000, "lon": 39.2800},
    "tazara": {"lat": -6.8344, "lon": 39.2540},
    "mandela_buguruni": {"lat": -6.8310, "lon": 39.2527},
    "kilwa_mbagala": {"lat": -6.8900, "lon": 39.2750},
    "old_bagamoyo": {"lat": -6.7770, "lon": 39.2600},
    "sam_nujoma": {"lat": -6.7865, "lon": 39.2320},
    "uhuru_street": {"lat": -6.8187, "lon": 39.2685},
    "posta_to_tegeta": {"lat": -6.7295, "lon": 39.2215},
    "posta_to_kimara": {"lat": -6.7980, "lon": 39.2190},
    "posta_to_gongolamboto": {"lat": -6.8505, "lon": 39.2275},
    "tabata_dampo": {"lat": -6.8225, "lon": 39.2185},
    "kamata_gerezani": {"lat": -6.8230, "lon": 39.2815},
    "changombe_road": {"lat": -6.8450, "lon": 39.2675},
    "morocco_intersection": {"lat": -6.7885, "lon": 39.2605},
    "kigogo_roundabout": {"lat": -6.8170, "lon": 39.2525},
    "fire_upanga": {"lat": -6.8070, "lon": 39.2750},
    "mwai_kibaki": {"lat": -6.7550, "lon": 39.2425},
    "sinza_mori": {"lat": -6.7740, "lon": 39.2400},
    "goba_massana": {"lat": -6.7200, "lon": 39.2000},
}


# --- 4. Helper Functions ---
@st.cache_data(ttl=60)
def get_live_data():
    docs = db.collection("live_traffic").stream()
    data = []
    for doc in docs:
        row = doc.to_dict()
        row["id"] = doc.id
        coords = ROAD_COORDS.get(doc.id, {"lat": -6.792, "lon": 39.239})
        row["lat"], row["lon"] = coords["lat"], coords["lon"]

        if row["status"] == "Smooth":
            row["color"] = [40, 167, 69, 200]
        elif row["status"] == "Moderate":
            row["color"] = [255, 193, 7, 220]
        else:
            row["color"] = [220, 53, 69, 255]

        row["elevation_val"] = max(row["delay_mins"], 0.5)
        data.append(row)
    return pd.DataFrame(data)


df_raw = get_live_data()

# --- 5. SIDEBAR: COMMAND CENTER ---
st.sidebar.title(":material/tune: COMMAND CENTER")

if st.sidebar.button(
    "Sync Live Telemetry", icon=":material/sync:", use_container_width=True
):
    st.toast(
        "Establishing uplink to satellite telemetry...", icon=":material/cell_tower:"
    )
    time.sleep(0.5)
    get_live_data.clear()
    st.toast("Database Synchronized.", icon=":material/check_circle:")
    time.sleep(0.5)
    st.rerun()

tz = pytz.timezone("Africa/Dar_es_Salaam")
st.sidebar.info(
    f"Local Time: {datetime.now(tz).strftime('%H:%M')}", icon=":material/schedule:"
)

status_filter = st.sidebar.multiselect(
    "Flow State Filter",
    ["Smooth", "Moderate", "Heavy Jam"],
    default=["Smooth", "Moderate", "Heavy Jam"],
)
df = df_raw[df_raw["status"].isin(status_filter)] if not df_raw.empty else df_raw

if not df.empty:
    csv = df.to_csv(index=False).encode("utf-8")
    st.sidebar.download_button(
        label="Export Live CSV",
        data=csv,
        file_name="dar_traffic_live.csv",
        icon=":material/download:",
    )

st.sidebar.markdown("---")
st.sidebar.markdown("### :material/memory: System Architecture")
st.sidebar.caption("**Telemetry:** Google Maps Enterprise API")
st.sidebar.caption("**Meteorology:** Open-Meteo Global API")
st.sidebar.caption("**Infrastructure:** Cloud Firestore & Actions")
st.sidebar.caption("Architected by John Mziray")

st.sidebar.markdown("---")
st.sidebar.markdown("### :material/model_training: MLOps Diagnostics")
if os.path.exists("model_metrics.csv"):
    try:
        metrics_df = pd.read_csv("model_metrics.csv")
        latest_metrics = metrics_df.iloc[-1]
        st.sidebar.metric(
            label="Predictive Error Margin (MAE)",
            value=f"± {latest_metrics['MAE_Minutes']} Mins",
        )
        st.sidebar.caption(
            f"**Training Vector:** {int(latest_metrics['Total_Rows_Trained']):,} isolated data points."
        )
        st.sidebar.caption(f"**Last Weights Update:** {latest_metrics['Date']}")
        if len(metrics_df) > 1:
            with st.sidebar.expander(":material/show_chart: View Learning Curve"):
                st.caption("Tracking Mean Absolute Error drift over time.")
                st.line_chart(metrics_df.set_index("Date")["MAE_Minutes"])
    except Exception as e:
        st.sidebar.caption("Parsing diagnostic metrics...")
else:
    st.sidebar.caption("Awaiting initial training cycle weights.")

# --- 6. MAIN DASHBOARD ---
st.title("DAR ES SALAAM SMART CITY ENGINE")
st.markdown("---")

if not df.empty:
    c1, c2, c3, c4 = st.columns(4)
    avg_speed = df_raw["speed_kmh"].mean()
    total_delay = df_raw["delay_mins"].sum()
    efficiency = 100 - min(
        (total_delay / 250) * 100, 100
    )  # Adjusted scale for 21 roads

    if "timestamp" in df_raw.columns:
        latest_time = pd.to_datetime(df_raw["timestamp"].max()).tz_convert(
            "Africa/Dar_es_Salaam"
        )
        time_str = latest_time.strftime("%I:%M %p")
    else:
        time_str = "Live"

    c1.metric("NETWORK EFFICIENCY", f"{efficiency:.1f}%")
    c2.metric("AVG VELOCITY", f"{avg_speed:.1f} km/h")
    c3.metric("TOTAL CITY DELAY", f"{total_delay} MIN")
    c4.metric("LAST SYNC", time_str, delta="Verified Telemetry", delta_color="normal")
    st.markdown("---")

    # --- GEN-AI COMMUTE COPILOT ---
    st.subheader(":material/podcasts: Generative AI Intelligence Brief")

    gemini_api_key = os.getenv("GEMINI_API_KEY") or (
        st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else None
    )

    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
        with st.expander("Request Automated Executive Summary", expanded=False):
            if st.button(
                "Generate Intelligence Brief",
                type="primary",
                icon=":material/graphic_eq:",
            ):
                with st.spinner("Analyzing macro-level routing data..."):
                    try:
                        worst_road = df_raw.loc[df_raw["delay_mins"].idxmax()]
                        best_road = df_raw.loc[df_raw["delay_mins"].idxmin()]
                        system_prompt = f"""
                        You are a highly professional, analytical AI traffic intelligence system for Dar es Salaam. 
                        Read the live telemetry data below and generate a crisp, executive-level routing advisory 
                        for commercial logistics and daily commuters.
                        
                        LIVE TELEMETRY:
                        - Network Flow: {efficiency:.1f}%
                        - Primary Bottleneck: {worst_road['name']} ({worst_road['delay_mins']} min delay). Weather: {worst_road['weather']}.
                        - Optimal Route: {best_road['name']} ({best_road['delay_mins']} min delay). Weather: {best_road['weather']}.
                        - Cumulative Delay: {total_delay} minutes across 21 monitored nodes.
                        
                        RULES:
                        1. Maximum 4 sentences.
                        2. Tone must be corporate, precise, and highly analytical.
                        3. Provide specific re-routing or timing advice based on the data.
                        4. Do NOT use markdown, emojis, or formatting. Plain text only.
                        """
                        model = genai.GenerativeModel("gemini-2.5-flash")
                        response = model.generate_content(system_prompt)
                        st.success(response.text, icon=":material/info:")
                        st.caption(
                            "Report compiled dynamically by Gemini 1.5 Flash using live Scikit-Learn pipelines."
                        )
                    except Exception as e:
                        st.error(
                            f"Generative AI Protocol Error: {e}",
                            icon=":material/warning:",
                        )
    else:
        st.info(
            "To enable AI Reporting, integrate a valid GEMINI_API_KEY in the environment.",
            icon=":material/key:",
        )

    st.markdown("---")

    # --- ECONOMIC IMPACT CALCULATOR ---
    st.subheader(":material/payments: Economic Friction Analytics")
    COST_PER_MINUTE_PER_CAR = 101
    ASSUMED_CARS_PER_NODE = 750  # Adjusted for Mega-Routes
    total_wasted_tzs = total_delay * COST_PER_MINUTE_PER_CAR * ASSUMED_CARS_PER_NODE

    if total_wasted_tzs >= 1000000:
        formatted_cost = f"{total_wasted_tzs / 1000000:.1f}M TZS"
    elif total_wasted_tzs >= 1000:
        formatted_cost = f"{total_wasted_tzs / 1000:.1f}K TZS"
    else:
        formatted_cost = f"{total_wasted_tzs:,.0f} TZS"

    eco1, eco2, eco3 = st.columns(3)
    with eco1:
        st.metric(
            label="Estimated Capital Friction (Live)",
            value=formatted_cost,
            delta="Wasted productivity",
            delta_color="inverse",
        )
    with eco2:
        liters_wasted = total_delay * 0.016 * ASSUMED_CARS_PER_NODE
        st.metric(
            label="Calculated Fuel Deficit",
            value=f"{liters_wasted:,.0f} Liters",
            delta="Idle consumption rate",
            delta_color="inverse",
        )
    with eco3:
        with st.expander(":material/calculate: Methodology Matrix"):
            st.caption(
                "Calculations assume baseline burn of 1L/hr and a median economic output of 3,000 TZS/hr per vehicle. Multiplied by an estimated density of 750 vehicles per active node."
            )

    st.markdown("---")

    # --- ADVANCED INTELLIGENCE & AI PREDICTION ---
    col_ai_left, col_ai_right = st.columns([1, 2])

    with col_ai_left:
        with st.container(border=True):
            st.subheader(":material/gpp_maybe: Autonomous System Alerts")
            bottleneck_row = df_raw.loc[df_raw["delay_mins"].idxmax()]

            if total_delay > 150:
                st.error(
                    f"**Critical Gridlock:** Severe volume detected at **{bottleneck_row['name']}**.",
                    icon=":material/gpp_bad:",
                )
            elif (
                "Rain" in df_raw["weather"].iloc[0]
                or "Drizzle" in df_raw["weather"].iloc[0]
            ):
                st.warning(
                    "**Meteorological Shift:** Precipitation impacting friction coefficients.",
                    icon=":material/water_drop:",
                )
            else:
                st.success(
                    "**Nominal Flow:** Arteries operating within acceptable thresholds.",
                    icon=":material/gpp_good:",
                )
            st.write(f"**Structural Efficiency:** {efficiency:.1f}%")
            st.progress(efficiency / 100)

    with col_ai_right:
        with st.container(border=True):
            st.subheader(":material/psychology: Predictive Traffic Modeling")
            if os.path.exists("traffic_model.pkl"):
                ai_model = joblib.load("traffic_model.pkl")

                road_options = {
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

                ai_p1, ai_p2, ai_p3, ai_p4 = st.columns(4)
                with ai_p1:
                    display_name = st.selectbox("Artery", list(road_options.values()))
                    p_road = list(road_options.keys())[
                        list(road_options.values()).index(display_name)
                    ]
                with ai_p2:
                    p_day = st.selectbox(
                        "Day",
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
                with ai_p3:
                    time_options = [
                        f"{h:02d}:{m:02d}"
                        for h in range(6, 24)
                        for m in (0, 15, 30, 45)
                    ]
                    current_hour = datetime.now(tz).hour
                    default_time = (
                        f"{current_hour:02d}:00" if 6 <= current_hour <= 23 else "08:00"
                    )
                    p_time_str = st.selectbox(
                        "Time",
                        time_options,
                        index=(
                            time_options.index(default_time)
                            if default_time in time_options
                            else time_options.index("08:00")
                        ),
                    )
                with ai_p4:
                    p_weather = st.selectbox("Weather", ["Clear", "Rainy", "Cloudy"])

                h, m = map(int, p_time_str.split(":"))
                target_fraction = h + (m / 60.0)
                start_frac = max(6.0, target_fraction - 1.25)
                end_frac = min(23.75, target_fraction + 1.25)
                step_count = int((end_frac - start_frac) / 0.25) + 1
                curve_hours = [start_frac + (i * 0.25) for i in range(step_count)]

                curve_df = pd.DataFrame(
                    {
                        "road_id": [p_road] * len(curve_hours),
                        "Hour": curve_hours,
                        "Day": [p_day] * len(curve_hours),
                        "Condition": [p_weather] * len(curve_hours),
                    }
                )
                curve_df["Predicted_Delay"] = ai_model.predict(curve_df)

                def format_frac_time(f):
                    hr = int(f)
                    mn = int(round((f - hr) * 60))
                    return f"{hr:02d}:{mn:02d}"

                curve_df["Time"] = curve_df["Hour"].apply(format_frac_time)
                exact_prediction = curve_df[curve_df["Hour"] == target_fraction][
                    "Predicted_Delay"
                ].values[0]

                st.metric(
                    label=f"Forecasting Delay for {p_time_str}",
                    value=f"{exact_prediction:.1f} Mins",
                )

                fig = px.line(
                    curve_df,
                    x="Time",
                    y="Predicted_Delay",
                    markers=True,
                    template="plotly_dark",
                    height=200,
                )
                fig.update_traces(line_color="#00d2ff", line_width=3)
                fig.update_layout(
                    margin=dict(l=0, r=0, t=10, b=0),
                    xaxis_title=None,
                    yaxis_title="Minutes",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(
                    "Predictive weights compiling. Model deployment pending.",
                    icon=":material/pending_actions:",
                )

    st.markdown("---")

    # --- UI LAYOUT: TABS ---
    tab1, tab2 = st.tabs(
        [
            ":material/language: 3D Geospatial Modeling",
            ":material/dataset: Granular Node Analytics",
        ]
    )

    with tab1:
        st.subheader(":material/map: 4D Geospatial Projection")
        st.caption(
            "Drag and pitch the map. Adjust the slider to project traffic density based on historical Random Forest patterns."
        )

        if os.path.exists("traffic_model.pkl"):
            ai_model = joblib.load("traffic_model.pkl")

            sim_c1, sim_c2 = st.columns(2)
            with sim_c1:
                sim_day = st.selectbox(
                    "Projection Day",
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
                    key="sim_day",
                )
            with sim_c2:
                sim_weather = st.selectbox(
                    "Projection Weather",
                    ["Clear", "Rainy", "Cloudy"],
                    key="sim_weather",
                )

            slider_hour = st.select_slider(
                "Geospatial Time State",
                options=[h for h in range(6, 24)],
                value=datetime.now(tz).hour if 6 <= datetime.now(tz).hour <= 23 else 8,
                format_func=lambda x: f"{x:02d}:00",
                key="sim_hour",
            )

            sim_data = []
            for r_id, coords in ROAD_COORDS.items():
                pred_df = pd.DataFrame(
                    {
                        "road_id": [r_id],
                        "Hour": [slider_hour],
                        "Day": [sim_day],
                        "Condition": [sim_weather],
                    }
                )
                pred_delay = ai_model.predict(pred_df)[0]
                if pred_delay < 2.0:
                    color, status = [40, 167, 69, 200], "Smooth"
                elif pred_delay < 6.0:
                    color, status = [255, 193, 7, 220], "Moderate"
                else:
                    color, status = [220, 53, 69, 255], "Heavy Jam"
                sim_data.append(
                    {
                        "name": r_id.replace("_", " ").title(),
                        "lat": coords["lat"],
                        "lon": coords["lon"],
                        "delay_mins": round(pred_delay, 1),
                        "status": status,
                        "color": color,
                        "elevation_val": max(pred_delay * 1.5, 0.5),
                    }
                )

            sim_df = pd.DataFrame(sim_data)
            tooltip = {
                "html": "<b style='font-family: sans-serif; font-size: 14px;'>{name}</b><br/>"
                + "Projected Flow: <span style='color: #00d2ff;'>{status}</span><br/>Calculated Delay: <b>{delay_mins} mins</b>",
                "style": {
                    "backgroundColor": "#121212",
                    "color": "#E0E0E0",
                    "border": "1px solid #333",
                    "borderRadius": "4px",
                    "padding": "8px",
                },
            }

            # Adjusted pitch and zoom for a more cinematic/enterprise view of the wider city
            view_state = pdk.ViewState(
                latitude=-6.80, longitude=39.24, zoom=10.5, pitch=60, bearing=0
            )
            layer = pdk.Layer(
                "ColumnLayer",
                sim_df,
                get_position=["lon", "lat"],
                get_elevation="elevation_val",
                elevation_scale=200,
                radius=350,
                get_fill_color="color",
                extruded=True,
                pickable=True,
                auto_highlight=True,
            )
            st.pydeck_chart(
                pdk.Deck(
                    layers=[layer],
                    initial_view_state=view_state,
                    tooltip=tooltip,
                    map_style="dark",
                )
            )
        else:
            st.info(
                "Geospatial modeling requires an active traffic_model.pkl binary.",
                icon=":material/info:",
            )

    with tab2:
        st.subheader(":material/table: Live Node Telemetry")
        num_cols = 3
        for i in range(0, len(df), num_cols):
            chunk = df.iloc[i : i + num_cols]
            cols = st.columns(num_cols)
            for index, row in chunk.reset_index().iterrows():
                with cols[index]:
                    css_class = (
                        "green"
                        if row["status"] == "Smooth"
                        else "yellow" if row["status"] == "Moderate" else "red"
                    )
                    with st.container(border=True):
                        st.markdown(
                            f"""
                            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                                <div class="blob {css_class}"></div>
                                <span style="font-weight: bold; letter-spacing: 1px; font-size: 0.9em; color: #E0E0E0;">{row['name'].upper()}</span>
                            </div>
                        """,
                            unsafe_allow_html=True,
                        )
                        st.metric(
                            label="Calculated Velocity",
                            value=f"{row['speed_kmh']} km/h",
                            delta=f"{row['delay_mins']} min variance",
                            delta_color="inverse",
                        )
                        st.progress(min(row["speed_kmh"] / 50.0, 1.0))
                        st.caption(
                            f":material/filter_drama: {row['weather'].upper()} | :material/hub: {row['id']}"
                        )

    with st.expander(
        ":material/architecture: System Architecture & Data Provenance", expanded=False
    ):
        st.markdown("""
        **Pipeline Specification:**
        * :material/dns: **Asynchronous Ingestion:** Cloud-native workers pinging Google Distance Matrix and Open-Meteo APIs on strict chron intervals.
        * :material/network_node: **Algorithmic Processing:** Scikit-Learn Random Forest Regressors extracting cyclic hour/day patterns across 21 high-variance city arteries.
        * :material/storage: **Data Layer:** Google Cloud Firestore NoSQL object storage.
        * :material/dashboard: **Visualization:** React-based Pydeck WebGL rendering for high-performance 3D spatial analytics.
        """)
else:
    st.info("No telemetry matching current parameters.", icon=":material/search_off:")
