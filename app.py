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

# --- 3. MASTER CITY GRID COORDINATES ---
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
                    docs = (
                        db.collection("traffic_history")
                        .order_by("timestamp", direction=firestore.Query.DESCENDING)
                        .stream()
                    )
                    history_df = pd.DataFrame([doc.to_dict() for doc in docs])

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
        layer = pdk.Layer(
            "ColumnLayer",
            df_raw,
            get_position=["lon", "lat"],
            get_elevation="elevation_val",
            elevation_scale=150,
            radius=300,
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
                            prompt = f"You are a logistics AI for Dar es Salaam. Flow is {efficiency:.1f}%. Worst road is {bottleneck_row['name']} with {bottleneck_row['delay_mins']} min delay. Write a 3-sentence professional executive summary for commercial fleets advising them on current conditions. No markdown."
                            #  UPDATED TO 3.5 FLASH HERE
                            response = genai.GenerativeModel(
                                "gemini-3.5-flash"
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
