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

# --- 1. Setup Page Config ---
st.set_page_config(
    page_title="Dar Traffic Intelligence",
    layout="wide",
    page_icon=":material/satellite_alt:",
)

# --- CUSTOM CSS ---
st.markdown(
    """
<style>
.blob { border-radius: 50%; margin-right: 12px; height: 14px; width: 14px; transform: scale(1); }
.blob.green { background: rgba(40, 167, 69, 1); animation: pulse-green 2s infinite; }
@keyframes pulse-green { 0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(40, 167, 69, 0.7); } 70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(40, 167, 69, 0); } 100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(40, 167, 69, 0); } }
.blob.yellow { background: rgba(255, 193, 7, 1); animation: pulse-yellow 2s infinite; }
@keyframes pulse-yellow { 0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 193, 7, 0.7); } 70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(255, 193, 7, 0); } 100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 193, 7, 0); } }
.blob.red { background: rgba(220, 53, 69, 1); animation: pulse-red 1.2s infinite; }
@keyframes pulse-red { 0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.8); } 70% { transform: scale(1.1); box-shadow: 0 0 0 12px rgba(220, 53, 69, 0); } 100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(220, 53, 69, 0); } }
.block-container { padding-top: 2rem; padding-bottom: 2rem; }
</style>
""",
    unsafe_allow_html=True,
)

# --- 2. Connect to Firebase (THE BULLETPROOF FIX) ---
if not firebase_admin._apps:
    try:
        if os.path.exists("firebase-key.json"):
            # Local development (Laptop)
            cred = credentials.Certificate("firebase-key.json")

        elif "firebase" in st.secrets:
            # Cloud deployment (Streamlit)
            if "key_data" in st.secrets["firebase"]:
                # If you pasted the JSON block inside triple quotes
                key_dict = json.loads(st.secrets["firebase"]["key_data"])
                cred = credentials.Certificate(key_dict)
            else:
                # If you used direct TOML, wrap the Streamlit secret in a standard dict()
                firebase_secrets = dict(st.secrets["firebase"])
                cred = credentials.Certificate(firebase_secrets)

        else:
            st.error("No valid Firebase credentials found.", icon=":material/error:")
            st.stop()

        firebase_admin.initialize_app(cred)

    except Exception as e:
        st.error(f"Connection Error: {e}", icon=":material/wifi_off:")
        st.stop()

db = firestore.client()

# --- 3. DAR ES SALAAM COORDINATES ---
ROAD_COORDS = {
    "kilwa_mbagala": {"lat": -6.892, "lon": 39.269},
    "mandela_buguruni": {"lat": -6.834, "lon": 39.248},
    "mwenge": {"lat": -6.778, "lon": 39.231},
    "old_bagamoyo": {"lat": -6.764, "lon": 39.264},
    "selander": {"lat": -6.801, "lon": 39.288},
    "tazara": {"lat": -6.835, "lon": 39.236},
    "ubungo": {"lat": -6.797, "lon": 39.218},
    "sam_nujoma": {"lat": -6.7865, "lon": 39.2320},
    "uhuru_street": {"lat": -6.8187, "lon": 39.2685},
    "kariakoo": {"lat": -6.8162, "lon": 39.2737},
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

# --- 5. SIDEBAR: Control Center ---
st.sidebar.title(":material/tune: COMMAND CENTER")

# UI Enhancement: Modern Toast Notifications for Sync
if st.sidebar.button(
    "Sync Live Telemetry", icon=":material/sync:", use_container_width=True
):
    st.toast("Pinging satellites...", icon="🛰️")
    time.sleep(0.5)
    get_live_data.clear()
    st.toast("Database Updated Successfully!", icon="✅")
    time.sleep(0.5)
    st.rerun()

tz = pytz.timezone("Africa/Dar_es_Salaam")
st.sidebar.info(
    f"Local Time: {datetime.now(tz).strftime('%H:%M')}", icon=":material/schedule:"
)

status_filter = st.sidebar.multiselect(
    "Status Filter",
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
st.sidebar.markdown("### :material/database: Data Provenance")
st.sidebar.caption("**Traffic Data:** Google Maps Distance Matrix API")
st.sidebar.caption("**Weather Data:** Open-Meteo Global API")
st.sidebar.caption("**Infrastructure:** Firebase & GitHub Actions")
st.sidebar.markdown("---")
st.sidebar.caption("Built by John Mziray | Data Engineering Portfolio")

# --- AI Model Health Sidebar Section ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 🧠 AI Model Health")

if os.path.exists("model_metrics.csv"):
    try:
        metrics_df = pd.read_csv("model_metrics.csv")
        latest_metrics = metrics_df.iloc[-1]

        st.sidebar.metric(
            label="Current AI Accuracy (Error Margin)",
            value=f"± {latest_metrics['MAE_Minutes']} Mins",
        )
        st.sidebar.caption(
            f"**Knowledge Base:** Trained on {int(latest_metrics['Total_Rows_Trained'])} historical data points."
        )
        st.sidebar.caption(f"**Last Retrained:** {latest_metrics['Date']}")

        if len(metrics_df) > 1:
            with st.sidebar.expander("📈 View Learning Curve"):
                st.caption("Lower error means the AI is getting smarter!")
                st.line_chart(metrics_df.set_index("Date")["MAE_Minutes"])

    except Exception as e:
        st.sidebar.caption("Parsing model metrics...")
else:
    st.sidebar.caption(
        "Model metrics will appear after the next automated training cycle."
    )

# --- 6. MAIN DASHBOARD ---
st.title("DAR ES SALAAM TRAFFIC INTELLIGENCE")
st.markdown("---")

if not df.empty:
    # --- ROW 1: City Health Hero ---
    c1, c2, c3, c4 = st.columns(4)
    avg_speed = df_raw["speed_kmh"].mean()
    total_delay = df_raw["delay_mins"].sum()
    efficiency = 100 - min((total_delay / 150) * 100, 100)

    if "timestamp" in df_raw.columns:
        latest_time = pd.to_datetime(df_raw["timestamp"].max()).tz_convert(
            "Africa/Dar_es_Salaam"
        )
        time_str = latest_time.strftime("%I:%M %p")
    else:
        time_str = "Live"

    c1.metric("NETWORK EFFICIENCY", f"{efficiency:.1f}%")
    c2.metric("AVG VELOCITY", f"{avg_speed:.1f} km/h")
    c3.metric("TOTAL DELAY", f"{total_delay} MIN")
    c4.metric(
        "LAST SYNC", time_str, delta="Verified by Google API", delta_color="normal"
    )

    st.markdown("---")

    # --- ECONOMIC IMPACT CALCULATOR ---
    st.subheader(":material/payments: Economic Impact of Congestion")

    # Economic Assumptions (TZS)
    COST_PER_MINUTE_PER_CAR = 101  # 50 TZS Time + 51 TZS Fuel
    ASSUMED_CARS_PER_NODE = 500  # Estimated traffic volume per road

    # Calculate the financial drain
    total_wasted_tzs = total_delay * COST_PER_MINUTE_PER_CAR * ASSUMED_CARS_PER_NODE

    # Format the number to look like beautiful currency (e.g., 1.2M TZS)
    if total_wasted_tzs >= 1000000:
        formatted_cost = f"{total_wasted_tzs / 1000000:.1f}M TZS"
    elif total_wasted_tzs >= 1000:
        formatted_cost = f"{total_wasted_tzs / 1000:.1f}K TZS"
    else:
        formatted_cost = f"{total_wasted_tzs:,.0f} TZS"

    eco1, eco2, eco3 = st.columns(3)

    with eco1:
        st.metric(
            label="Estimated Capital Lost (Live)",
            value=formatted_cost,
            delta="Burning fuel & lost wages",
            delta_color="inverse",
        )
    with eco2:
        # Just a fun metric to show what that money could have bought
        liters_wasted = total_delay * 0.016 * ASSUMED_CARS_PER_NODE
        st.metric(
            label="Total Fuel Wasted",
            value=f"{liters_wasted:,.0f} Liters",
            delta="Idle consumption",
            delta_color="inverse",
        )
    with eco3:
        with st.expander("How is this calculated?"):
            st.caption(
                "We assume an average fuel burn of 1L/hr and a median wage value of 3,000 TZS/hr per vehicle. Multiplied by an estimated volume of 500 cars per tracked intersection."
            )

    st.markdown("---")

    # --- ADVANCED INTELLIGENCE & AI PREDICTION ---
    col_ai_left, col_ai_right = st.columns([1, 2])

    with col_ai_left:
        with st.container(border=True):
            st.subheader(":material/memory: System Alerts")
            bottleneck_row = df_raw.loc[df_raw["delay_mins"].idxmax()]

            if total_delay > 60:
                st.error(
                    f"**Gridlock Detected:** Severe congestion at **{bottleneck_row['name']}**.",
                    icon=":material/gpp_bad:",
                )
            elif (
                "Rain" in df_raw["weather"].iloc[0]
                or "Drizzle" in df_raw["weather"].iloc[0]
            ):
                st.warning(
                    "**Weather Advisory:** Precipitation detected. Flow efficiency expected to drop.",
                    icon=":material/rainy:",
                )
            else:
                st.success(
                    "**Optimal Flow:** City traffic is moving within normal parameters.",
                    icon=":material/gpp_good:",
                )

            st.write(f"**City Flow Efficiency:** {efficiency:.1f}%")
            st.progress(efficiency / 100)

    with col_ai_right:
        with st.container(border=True):
            st.subheader(":material/psychology: AI Traffic Predictor")

            if os.path.exists("traffic_model.pkl"):
                ai_model = joblib.load("traffic_model.pkl")

                ai_p1, ai_p2, ai_p3, ai_p4 = st.columns(4)

                with ai_p1:
                    p_road = st.selectbox("Road", list(ROAD_COORDS.keys()))
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
                    label=f"Predicted Delay for {p_time_str}",
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
                    yaxis_title="Mins Delay",
                )

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(
                    "AI model is currently training. Automated retraining happens weekly.",
                    icon=":material/pending_actions:",
                )

    st.markdown("---")

    # --- UI LAYOUT: TABS ---
    tab1, tab2 = st.tabs(
        [
            ":material/3d_rotation: 3D Node Map",
            ":material/analytics: Detailed Node Analysis",
        ]
    )

    with tab1:
        st.subheader(":material/3d_rotation: 4D Geospatial Time Machine")
        st.caption(
            "Watch the city's traffic pulse throughout the day. Powered by your Random Forest AI Model."
        )

        if os.path.exists("traffic_model.pkl"):
            ai_model = joblib.load("traffic_model.pkl")

            # --- 1. Simulation Controls ---
            sim_c1, sim_c2, sim_c3 = st.columns([2, 2, 1])
            with sim_c1:
                sim_day = st.selectbox(
                    "Simulation Day",
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
                    "Simulation Weather",
                    ["Clear", "Rainy", "Cloudy"],
                    key="sim_weather",
                )
            with sim_c3:
                st.write("")  # Spacing alignment
                st.write("")
                play_animation = st.button(
                    "▶ Play Animation", use_container_width=True, type="primary"
                )

            slider_hour = st.slider(
                "Manual Time Travel (Hour)",
                min_value=6,
                max_value=23,
                value=8,
                step=1,
                key="sim_hour",
            )

            # --- 2. The AI Rendering Engine ---
            def generate_pydeck_map(target_hour):
                sim_data = []
                for r_id, coords in ROAD_COORDS.items():
                    # Feed the AI the specific hour, day, and weather for this specific road
                    pred_df = pd.DataFrame(
                        {
                            "road_id": [r_id],
                            "Hour": [target_hour],
                            "Day": [sim_day],
                            "Condition": [sim_weather],
                        }
                    )
                    pred_delay = ai_model.predict(pred_df)[0]

                    # Dynamically adjust colors based on the AI's prediction
                    if pred_delay < 1.0:
                        color = [40, 167, 69, 200]  # Green (Smooth)
                        status = "Smooth"
                    elif pred_delay < 2.5:
                        color = [255, 193, 7, 220]  # Yellow (Moderate)
                        status = "Moderate"
                    else:
                        color = [220, 53, 69, 255]  # Red (Heavy Jam)
                        status = "Heavy Jam"

                    sim_data.append(
                        {
                            "name": r_id.replace("_", " ").title(),
                            "lat": coords["lat"],
                            "lon": coords["lon"],
                            "delay_mins": round(pred_delay, 1),
                            "status": status,
                            "color": color,
                            "elevation_val": max(
                                pred_delay * 1.5, 0.5
                            ),  # Scale height for visual impact
                        }
                    )

                sim_df = pd.DataFrame(sim_data)

                # Build the 3D Map
                tooltip = {
                    "html": "<b>{name}</b><br/>Simulated Time: "
                    + f"{int(target_hour):02d}:00"
                    + "<br/>Status: {status}<br/>Predicted Delay: {delay_mins} mins",
                    "style": {
                        "backgroundColor": "#1E1E1E",
                        "color": "white",
                        "border": "1px solid #333",
                        "borderRadius": "4px",
                    },
                }
                view_state = pdk.ViewState(
                    latitude=-6.81, longitude=39.25, zoom=11.5, pitch=50, bearing=0
                )
                layer = pdk.Layer(
                    "ColumnLayer",
                    sim_df,
                    get_position=["lon", "lat"],
                    get_elevation="elevation_val",
                    elevation_scale=150,
                    radius=250,
                    get_fill_color="color",
                    extruded=True,
                    pickable=True,
                    auto_highlight=True,
                )
                return pdk.Deck(
                    layers=[layer],
                    initial_view_state=view_state,
                    tooltip=tooltip,
                    map_style="dark",
                )

            # --- 3. The Animation Loop ---
            map_placeholder = st.empty()  # Creates a blank container we can overwrite

            if play_animation:
                # Loop through the day and overwrite the map every 0.6 seconds
                for h in range(6, 24):
                    with map_placeholder.container():
                        st.markdown(
                            f"<h4 style='text-align: center; color: #00d2ff;'>⏰ Simulating Time: {h:02d}:00</h4>",
                            unsafe_allow_html=True,
                        )
                        st.pydeck_chart(generate_pydeck_map(h))
                    time.sleep(0.6)
                st.toast("Simulation Complete!", icon="✅")
            else:
                # Static render based on where the user drags the slider
                with map_placeholder.container():
                    st.markdown(
                        f"<h4 style='text-align: center; color: #9e9e9e;'>⏰ Time: {slider_hour:02d}:00</h4>",
                        unsafe_allow_html=True,
                    )
                    st.pydeck_chart(generate_pydeck_map(slider_hour))

        else:
            st.info(
                "The AI model needs to finish training before the Time Machine can simulate city-wide traffic.",
                icon=":material/info:",
            )
            # (Fallback: Shows nothing until the AI model is ready)

    with tab2:
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
                            label="Velocity",
                            value=f"{row['speed_kmh']} km/h",
                            delta=f"{row['delay_mins']} min delay",
                            delta_color="inverse",
                        )
                        st.progress(min(row["speed_kmh"] / 50.0, 1.0))
                        st.caption(
                            f":material/cloud: {row['weather'].upper()} | :material/router: {row['id']}"
                        )

    # --- FOOTER: METHODOLOGY ---
    with st.expander(
        ":material/science: How does this dashboard work?", expanded=False
    ):
        st.markdown("""
        **The Architecture of Trust:**
        * :material/memory: **Autonomous Ingestion:** GitHub Actions asynchronous server monitoring Google Maps Enterprise & Open-Meteo APIs.
        * :material/account_tree: **Machine Learning:** Scikit-Learn Random Forest Regressor calculates exact fractional-hour predictions across 10 global road networks.
        * :material/database: **Cloud Storage:** Google Cloud Firestore NoSQL Database.
        * :material/speed: **Live Rendering:** Real-time 3D telemetry rendering via Streamlit and Pydeck.
        """)
else:
    st.info("No data available based on current filters.", icon=":material/info:")
