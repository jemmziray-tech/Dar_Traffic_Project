import os
import json
from datetime import datetime
import pytz
import pandas as pd
import pydeck as pdk
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# --- 1. Setup Page Config ---
st.set_page_config(page_title="Dar Traffic Intelligence", layout="wide")

# --- CUSTOM CSS: PULSING RADAR ANIMATIONS ---
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
</style>
""",
    unsafe_allow_html=True,
)

# --- 2. Connect to Firebase ---
if not firebase_admin._apps:
    try:
        if os.path.exists("firebase-key.json"):
            cred = credentials.Certificate("firebase-key.json")
        elif "firebase" in st.secrets:
            key_dict = json.loads(st.secrets["firebase"]["key_data"])
            cred = credentials.Certificate(key_dict)
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
@st.cache_data(ttl=60)  # Caches data for 60 seconds
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
            row["color"] = [255, 193, 7, 200]
        else:
            row["color"] = [220, 53, 69, 255]
        data.append(row)
    return pd.DataFrame(data)


df_raw = get_live_data()

# --- 5. SIDEBAR: Control Center ---
st.sidebar.title(":material/tune: COMMAND CENTER")
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
        ":material/download: Export Live CSV",
        data=csv,
        file_name="dar_traffic_live.csv",
    )
st.sidebar.caption("Built by John Mziray | Data Engineering Portfolio")

# --- 6. MAIN DASHBOARD ---
st.title("DAR ES SALAAM TRAFFIC INTELLIGENCE")
st.markdown("---")

if not df.empty:
    c1, c2, c3 = st.columns(3)
    avg_speed = df_raw["speed_kmh"].mean()
    total_delay = df_raw["delay_mins"].sum()
    efficiency = 100 - min((total_delay / 150) * 100, 100)

    c1.metric("NETWORK EFFICIENCY", f"{efficiency:.1f}%")
    c2.metric("AVG VELOCITY", f"{avg_speed:.1f} km/h")
    c3.metric("TOTAL DELAY", f"{total_delay} MIN")

    with st.expander(":material/memory: Advanced System Intelligence", expanded=True):
        ai_col1, ai_col2 = st.columns([2, 1])
        with ai_col1:
            bottleneck_row = df_raw.loc[df_raw["delay_mins"].idxmax()]
            if total_delay > 60:
                st.error(
                    f"**Significant Gridlock:** High congestion at **{bottleneck_row['name']}**.",
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
        with ai_col2:
            st.write(f"**City Flow Efficiency:** {efficiency:.1f}%")
            st.progress(efficiency / 100)

    st.markdown("---")
    tab1, tab2 = st.tabs(
        [":material/map: Live Map View", ":material/analytics: Detailed Node Analysis"]
    )

    with tab1:
        tooltip = {
            "html": "<b>{name}</b><br/>Speed: {speed_kmh} km/h<br/>Status: {status}",
            "style": {"backgroundColor": "black", "color": "white"},
        }
        view_state = pdk.ViewState(latitude=-6.81, longitude=39.25, zoom=11, pitch=45)
        layer = pdk.Layer(
            "ScatterplotLayer",
            df,
            get_position=["lon", "lat"],
            get_color="color",
            get_radius=400,
            pickable=True,
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
else:
    st.info("No data available based on current filters.", icon=":material/info:")
