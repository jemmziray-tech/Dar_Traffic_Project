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
import google.generativeai as genai
from dotenv import load_dotenv

# Load Environment Variables securely
load_dotenv()

# --- 1. Setup Page Config ---
st.set_page_config(
    page_title="Dar Traffic Command",
    layout="wide",
    page_icon=":material/satellite_alt:",
    initial_sidebar_state="expanded",
)

# --- CUSTOM CSS ---
st.markdown(
    """
<style>
.blob { border-radius: 50%; margin-right: 8px; height: 10px; width: 10px; display: inline-block; transform: scale(1); }
.blob.green { background: rgba(40, 167, 69, 1); box-shadow: 0 0 8px rgba(40, 167, 69, 0.8); animation: pulse 2s infinite;}
.blob.yellow { background: rgba(255, 193, 7, 1); box-shadow: 0 0 8px rgba(255, 193, 7, 0.8); }
.blob.red { background: rgba(220, 53, 69, 1); box-shadow: 0 0 8px rgba(220, 53, 69, 0.8); }
@keyframes pulse { 
    0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(40, 167, 69, 0.7); } 
    70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(40, 167, 69, 0); } 
    100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(40, 167, 69, 0); } 
}
div[data-testid="stMetricValue"] { font-weight: 600; letter-spacing: -0.5px; }
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
</style>
""",
    unsafe_allow_html=True,
)


# --- 2. Connect to Firebase ---
@st.cache_resource
def init_system():
    if not firebase_admin._apps:
        if os.path.exists("firebase-key.json"):
            cred = credentials.Certificate("firebase-key.json")
        elif "firebase" in st.secrets:
            key_dict = (
                json.loads(st.secrets["firebase"]["key_data"])
                if "key_data" in st.secrets["firebase"]
                else dict(st.secrets["firebase"])
            )
            cred = credentials.Certificate(key_dict)
        else:
            st.error(
                "Authentication Failure: No Firebase credentials.",
                icon=":material/lock:",
            )
            st.stop()
        firebase_admin.initialize_app(cred)
    return firestore.client()


db = init_system()

# --- 3. MASTER CITY GRID COORDINATES & PATHS ---
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

ROAD_PATHS = {
    "ubungo": [[39.2201, -6.7978], [39.2300, -6.8040]],
    "mwenge": [[39.2431, -6.7744], [39.2489, -6.7631]],
    "selander": [[39.2750, -6.7950], [39.2850, -6.8050]],
    "tazara": [[39.2600, -6.8288], [39.2480, -6.8400]],
    "mandela_buguruni": [[39.2435, -6.8285], [39.2620, -6.8335]],
    "kilwa_mbagala": [[39.2700, -6.9050], [39.2800, -6.8750]],
    "old_bagamoyo": [[39.2550, -6.7720], [39.2650, -6.7820]],
    "sam_nujoma": [[39.2435, -6.7755], [39.2205, -6.7975]],
    "uhuru_street": [[39.2550, -6.8220], [39.2820, -6.8155]],
    "kariakoo": [[39.2725, -6.8115], [39.2750, -6.8210]],
    "posta_to_tegeta": [[39.2880, -6.8160], [39.1550, -6.6430]],
    "posta_to_kimara": [[39.2880, -6.8160], [39.1500, -6.7800]],
    "posta_to_gongolamboto": [[39.2880, -6.8160], [39.1670, -6.8850]],
    "tabata_dampo": [[39.2320, -6.8150], [39.2050, -6.8300]],
    "kamata_gerezani": [[39.2780, -6.8280], [39.2850, -6.8180]],
    "changombe_road": [[39.2700, -6.8350], [39.2650, -6.8550]],
    "morocco_intersection": [[39.2630, -6.7820], [39.2580, -6.7950]],
    "kigogo_roundabout": [[39.2550, -6.8120], [39.2500, -6.8220]],
    "fire_upanga": [[39.2780, -6.8120], [39.2720, -6.8020]],
    "mwai_kibaki": [[39.2350, -6.7450], [39.2500, -6.7650]],
    "sinza_mori": [[39.2350, -6.7780], [39.2450, -6.7700]],
    "goba_massana": [[39.2150, -6.7250], [39.1850, -6.7150]]
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
        row["path"] = ROAD_PATHS.get(doc.id, [[coords["lon"], coords["lat"]], [coords["lon"] + 0.005, coords["lat"] + 0.005]])
        row["color"] = (
            [220, 53, 69, 255]
            if row["delay_mins"] > 10
            else ([255, 193, 7, 220] if row["delay_mins"] > 4 else [40, 167, 69, 200])
        )
        row["elevation_val"] = max(row["delay_mins"] * 3, 0.5)
        data.append(row)
    return pd.DataFrame(data)


df_raw = get_live_data()
tz = pytz.timezone("Africa/Dar_es_Salaam")

# --- 5. SIDEBAR: COMMAND CENTER ---
with st.sidebar:
    st.title(":material/memory: System Core")
    st.markdown(
        '<div class="blob green"></div> **Live Network Active**', unsafe_allow_html=True
    )
    st.caption(f"Local Time: {datetime.now(tz).strftime('%H:%M %Z')}")
    st.divider()

    # --- MLOps Model Health Badge ---
    if os.path.exists("model_metrics.csv"):
        try:
            metrics_df = pd.read_csv("model_metrics.csv")
            if not metrics_df.empty:
                latest = metrics_df.iloc[-1]
                mae_val = latest.get("MAE_Minutes", 0.0)
                r2_val = latest.get("R2_Score", 0.0)
                st.markdown(
                    f"""
                    <div style="background: rgba(40, 167, 69, 0.12); border: 1px solid rgba(40, 167, 69, 0.4); border-radius: 8px; padding: 12px; margin-bottom: 12px;">
                        <div style="font-size: 0.85em; color: #28a745; font-weight: 600; display: flex; align-items: center; gap: 6px;">
                            <span>●</span> MODEL HEALTH: OPTIMAL
                        </div>
                        <div style="font-size: 0.8em; color: #E0E0E0; margin-top: 6px; line-height: 1.5;">
                            <b>MAE Variance:</b> ±{mae_val:.2f} mins<br/>
                            <b>R² Accuracy:</b> {r2_val:.3f}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        except Exception:
            pass

    if st.button(
        "Force Satellite Sync", icon=":material/sync:", use_container_width=True
    ):
        get_live_data.clear()
        st.rerun()

    st.subheader("Data Export")
    if not df_raw.empty:
        st.download_button(
            "Download Live CSV",
            data=df_raw.to_csv(index=False).encode("utf-8"),
            file_name="dar_traffic_live.csv",
            icon=":material/download:",
            use_container_width=True,
        )

    # Historical Archive Compiler
    with st.expander(":material/folder_zip: Full History Archive", expanded=False):
        st.caption("Export all historical telemetry since Day 1.")

        if "full_csv" not in st.session_state:
            if st.button(
                "Compile Database Archive",
                icon=":material/archive:",
                use_container_width=True,
            ):
                with st.spinner("Querying Firebase (This may take a moment)..."):
                    docs = db.collection("traffic_history").stream()
                    history_df = pd.DataFrame([doc.to_dict() for doc in docs])
                    if not history_df.empty and "timestamp" in history_df.columns:
                        history_df["timestamp_dt"] = pd.to_datetime(history_df["timestamp"], utc=True)
                        history_df = history_df.sort_values("timestamp_dt", ascending=False).drop(columns=["timestamp_dt"])

                    if not history_df.empty:
                        st.session_state.full_csv = history_df.to_csv(
                            index=False
                        ).encode("utf-8")
                        st.session_state.archive_date = datetime.now(tz).strftime(
                            "%Y%m%d"
                        )
                        st.rerun()
                    else:
                        st.error("Database is empty.", icon=":material/error:")

        if "full_csv" in st.session_state:
            st.success("Archive Ready!", icon=":material/check_circle:")
            st.download_button(
                label="Download Archive.csv",
                data=st.session_state.full_csv,
                file_name=f"dar_traffic_full_archive_{st.session_state.archive_date}.csv",
                mime="text/csv",
                icon=":material/download:",
                use_container_width=True,
            )

    st.divider()
    st.caption("Architected by John Mziray")

# --- 6. TOP KPIs ---
st.title("Dar es Salaam Smart City Engine")
st.markdown("---")

if not df_raw.empty:
    avg_speed = df_raw["speed_kmh"].mean()
    total_delay = df_raw["delay_mins"].sum()
    efficiency = 100 - min((total_delay / 250) * 100, 100)
    total_wasted_tzs = total_delay * 101 * 750

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Network Efficiency", f"{efficiency:.1f}%")
    k2.metric("Average Velocity", f"{avg_speed:.1f} km/h")
    k3.metric("Cumulative Gridlock", f"{total_delay} Mins")
    k4.metric(
        "Capital Friction (Live)",
        (
            f"{total_wasted_tzs / 1000000:.1f}M TZS"
            if total_wasted_tzs >= 1000000
            else f"{total_wasted_tzs:,.0f} TZS"
        ),
        delta="Wasted Productivity",
        delta_color="inverse",
    )

    st.write("")

    # --- 7. THE HIDDEN 4D MAP ---
    with st.expander(
        ":material/public: Open Live Spatial Grid (4D Digital Twin)", expanded=False
    ):
        st.caption(
            "Live geospatial density visualization of current traffic conditions."
        )
        tooltip = {
            "html": "<b style='font-family: sans-serif; font-size: 14px;'>{name}</b><br/>Live Delay: <b>{delay_mins} mins</b>",
            "style": {
                "backgroundColor": "#121212",
                "color": "white",
                "borderRadius": "4px",
                "padding": "8px",
            },
        }
        view_state = pdk.ViewState(
            latitude=-6.80, longitude=39.24, zoom=10.8, pitch=55, bearing=0
        )
        path_layer = pdk.Layer(
            "PathLayer",
            df_raw,
            get_path="path",
            get_color="color",
            width_scale=20,
            width_min_pixels=5,
            get_width=10,
            pickable=True,
            auto_highlight=True,
        )
        column_layer = pdk.Layer(
            "ColumnLayer",
            df_raw,
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
                layers=[path_layer, column_layer],
                initial_view_state=view_state,
                tooltip=tooltip,
                map_style="dark",
            )
        )

    st.write("")

    # --- 8. MAIN DASHBOARD SPLIT ---
    col_alerts, col_feed = st.columns([1, 2], gap="large")

    with col_alerts:
        with st.container(border=True):
            st.subheader(":material/gpp_maybe: Network Status")
            bottleneck_row = df_raw.loc[df_raw["delay_mins"].idxmax()]
            if total_delay > 150:
                st.error(
                    f"**Critical:** Severe volume at {bottleneck_row['name']}.",
                    icon=":material/gpp_bad:",
                )
            elif "Rain" in str(df_raw["weather"].iloc[0]) or "Drizzle" in str(
                df_raw["weather"].iloc[0]
            ):
                st.warning(
                    "**Weather:** Precipitation impacting flow.",
                    icon=":material/water_drop:",
                )
            else:
                st.success(
                    "**Optimal:** Arteries flowing nominally.",
                    icon=":material/gpp_good:",
                )

            st.write(f"**Structural Efficiency:** {efficiency:.1f}%")
            st.progress(efficiency / 100)

        st.write("")

        with st.container(border=True):
            st.subheader(":material/robot_2: AI Executive Briefing")
            st.caption("Generates a live macro-summary for logistics planning.")
            gemini_key = os.getenv("GEMINI_API_KEY") or (
                st.secrets.get("GEMINI_API_KEY")
                if "GEMINI_API_KEY" in st.secrets
                else None
            )

            if gemini_key:
                genai.configure(api_key=gemini_key)
                if st.button(
                    "Generate Dispatch Report",
                    type="primary",
                    use_container_width=True,
                    icon=":material/graphic_eq:",
                ):
                    with st.spinner("Analyzing macro-level routing data..."):
                        try:
                            prompt = f"You are a logistics AI for Dar es Salaam. Flow is {efficiency:.1f}%. Worst road is {bottleneck_row['name']} with {bottleneck_row['delay_mins']} min delay. Write a 3-sentence professional executive summary for commercial fleets in native swahili advising them on current conditions. No markdown."
                            response = genai.GenerativeModel(
                                "gemini-2.5-flash"
                            ).generate_content(prompt)
                            st.info(response.text)
                        except Exception as e:
                            st.error(f"Generative AI API Error: {e}")
            else:
                st.info(
                    "Provide GEMINI_API_KEY in environment to enable AI Briefings.",
                    icon=":material/key:",
                )

    with col_feed:
        st.subheader(":material/table: Live Node Telemetry Feed")
        df_sorted = df_raw.sort_values(by="delay_mins", ascending=False).reset_index(
            drop=True
        )

        num_cols = 3
        for i in range(0, min(9, len(df_sorted)), num_cols):
            chunk = df_sorted.iloc[i : i + num_cols]
            cols = st.columns(num_cols)
            for index, row in chunk.reset_index().iterrows():
                with cols[index]:
                    css_class = (
                        "green"
                        if row["delay_mins"] <= 4
                        else ("yellow" if row["delay_mins"] <= 10 else "red")
                    )
                    with st.container(border=True):
                        st.markdown(
                            f"""
                            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                                <div class="blob {css_class}"></div>
                                <span style="font-weight: 600; font-size: 0.85em; color: #E0E0E0;">{row['name'].upper()}</span>
                            </div>
                        """,
                            unsafe_allow_html=True,
                        )
                        st.metric(
                            label="Calculated Velocity",
                            value=f"{row['speed_kmh']} km/h",
                            delta=f"{row['delay_mins']} min delay",
                            delta_color="inverse",
                        )
                        st.progress(min(row["speed_kmh"] / 50.0, 1.0))
                        st.caption(f":material/filter_drama: {row['weather'].upper()}")

        if len(df_sorted) > 9:
            st.caption(
                f"... and {len(df_sorted) - 9} other nodes operating within nominal thresholds."
            )

else:
    st.info("Awaiting telemetry uplink...", icon=":material/cell_tower:")
