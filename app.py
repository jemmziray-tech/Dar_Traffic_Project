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
        tooltip = {
            "html": "<b>{name}</b><br/>Speed: {speed_kmh} km/h<br/>Status: {status}<br/>Delay: {delay_mins} mins",
            "style": {
                "backgroundColor": "#1E1E1E",
                "color": "white",
                "border": "1px solid #333",
                "borderRadius": "4px",
            },
        }
        view_state = pdk.ViewState(
            latitude=-6.81, longitude=39.25, zoom=11.5, pitch=45, bearing=0
        )
        layer = pdk.Layer(
            "ColumnLayer",
            df,
            get_position=["lon", "lat"],
            get_elevation="elevation_val",
            elevation_scale=150,
            radius=250,
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
