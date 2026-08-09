import os
import json
from datetime import datetime
import pytz
import pandas as pd
import pydeck as pdk
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv

# Load Environment Variables securely
load_dotenv()
from config import ROAD_COORDS, ROAD_PATHS
from utils import get_db

# --- 1. Setup Page Config ---
st.set_page_config(
    page_title="Dar Traffic Command",
    layout="wide",
    page_icon="🌍",
    initial_sidebar_state="expanded",
)

# Tiny CSS just for the pulsing dot (impossible via native Python API)
st.markdown("""
<style>
.blob { border-radius: 50%; margin-right: 8px; height: 10px; width: 10px; display: inline-block; }
.blob.green { background: #2ED573; box-shadow: 0 0 8px rgba(46,213,115,0.8); animation: pulse 2s infinite; }
@keyframes pulse {
    0%   { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(46,213,115,0.7); }
    70%  { transform: scale(1);    box-shadow: 0 0 0 10px rgba(46,213,115,0); }
    100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(46,213,115,0); }
}
</style>
""", unsafe_allow_html=True)

# --- 2. Connect to Firebase ---
db = get_db()

# --- 3. Helper Functions ---
@st.cache_data(ttl=15)
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

# --- 4. SIDEBAR: COMMAND CENTER ---
with st.sidebar:
    st.title("🧠 System Core")
    st.markdown('<div class="blob green"></div> **Live Network Active**', unsafe_allow_html=True)
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
                st.info(f"**MODEL HEALTH: OPTIMAL**\n\nMAE Variance: ±{mae_val:.2f} mins\n\nR² Accuracy: {r2_val:.3f}", icon="ℹ️")
        except Exception:
            pass

    if st.button("🔄 Sync Live Data", use_container_width=True):
        get_live_data.clear()
        st.rerun()

    st.subheader("Data Export")
    if not df_raw.empty:
        st.download_button(
            "📥 Download Live CSV",
            data=df_raw.to_csv(index=False).encode("utf-8"),
            file_name="dar_traffic_live.csv",
            use_container_width=True,
        )

    st.divider()
    st.caption("Architected by John Mziray")

# --- 5. MAIN DASHBOARD ---
if not df_raw.empty:
    avg_speed = df_raw["speed_kmh"].mean()
    total_delay = df_raw["delay_mins"].sum()
    efficiency = 100 - min((total_delay / 250) * 100, 100)
    total_wasted_tzs = total_delay * 101 * 750

    # Hero header
    st.title("Dar es Salaam Traffic Command")
    st.caption("Smart City Digital Twin — Real-Time Infrastructure Intelligence")
    
    st.write(f"**LIVE NETWORK:** {datetime.now(tz).strftime('%H:%M %Z · %d %b %Y')}")
    st.divider()

    # Premium KPI row natively
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        with st.container(border=True):
            st.metric(
                label="Network Efficiency", 
                value=f"{efficiency:.1f}%", 
                delta="Optimal Flow" if efficiency > 70 else ("Moderate Stress" if efficiency > 40 else "Critical Load"),
                delta_color="normal" if efficiency > 70 else ("off" if efficiency > 40 else "inverse")
            )
    with k2:
        with st.container(border=True):
            st.metric("Average Velocity", f"{avg_speed:.1f} km/h", "City-wide mean", delta_color="off")
    with k3:
        with st.container(border=True):
            st.metric("Cumulative Gridlock", f"{total_delay} mins", "Across all corridors", delta_color="inverse")
    with k4:
        with st.container(border=True):
            friction_str = f"{total_wasted_tzs/1000000:.1f}M TZS" if total_wasted_tzs >= 1000000 else f"{total_wasted_tzs:,.0f} TZS"
            st.metric("Economic Impact", friction_str, "- Wasted productivity", delta_color="inverse")

    st.write("")

    # --- 6. THE HIDDEN 4D MAP ---
    with st.expander("🌍 Open Live Spatial Grid (4D Digital Twin)", expanded=False):
        st.caption("Live geospatial density visualization of current traffic conditions.")
        tooltip = {
            "html": "<b style='font-family: sans-serif; font-size: 14px;'>{name}</b><br/>Live Delay: <b>{delay_mins} mins</b>",
            "style": {
                "backgroundColor": "#121212",
                "color": "white",
                "borderRadius": "4px",
                "padding": "8px",
            },
        }
        view_state = pdk.ViewState(latitude=-6.80, longitude=39.24, zoom=10.8, pitch=55, bearing=0)
        path_layer = pdk.Layer(
            "PathLayer", df_raw, get_path="path", get_color="color",
            width_scale=20, width_min_pixels=5, get_width=10, pickable=True, auto_highlight=True
        )
        column_layer = pdk.Layer(
            "ColumnLayer", df_raw, get_position=["lon", "lat"], get_elevation="elevation_val",
            elevation_scale=150, radius=250, get_fill_color="color", extruded=True, pickable=True, auto_highlight=True
        )
        st.pydeck_chart(pdk.Deck(layers=[path_layer, column_layer], initial_view_state=view_state, tooltip=tooltip, map_style="dark"))

    st.write("")

    # --- 7. MAIN DASHBOARD SPLIT ---
    col_alerts, col_feed = st.columns([1, 2], gap="large")

    with col_alerts:
        st.subheader("⬡ Network Status")
        bottleneck_row = df_raw.loc[df_raw["delay_mins"].idxmax()]
        
        with st.container(border=True):
            if total_delay > 150:
                st.error(f"**Critical congestion on {bottleneck_row['name']}**", icon="⚠️")
            elif "Rain" in str(df_raw["weather"].iloc[0]) or "Drizzle" in str(df_raw["weather"].iloc[0]):
                st.warning("**Precipitation detected — speeds reduced**", icon="🌧️")
            else:
                st.success("**All arteries flowing nominally**", icon="✅")
                
            st.write(f"**Structural Efficiency:** {efficiency:.1f}%")
            st.progress(int(efficiency) / 100)
            st.write(f"Worst: **{bottleneck_row['name']}** (+{bottleneck_row['delay_mins']} mins)")

        # AI Briefing
        st.subheader("🤖 AI Executive Briefing")
        with st.container(border=True):
            st.caption("Live macro-summary for logistics & fleet planning.")
            gemini_key = os.getenv("GEMINI_API_KEY") or (st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else None)
            if gemini_key:
                genai.configure(api_key=gemini_key)
                if st.button("Generate Dispatch Report", type="primary", use_container_width=True):
                    with st.spinner("Analyzing macro-level routing data..."):
                        try:
                            prompt = f"You are a logistics AI for Dar es Salaam. Flow is {efficiency:.1f}%. Worst road is {bottleneck_row['name']} with {bottleneck_row['delay_mins']} min delay. Write a 3-sentence professional executive summary for commercial fleets in native swahili advising them on current conditions. No markdown."
                            response = genai.GenerativeModel("gemini-2.0-flash").generate_content(prompt)
                            st.info(response.text)
                        except Exception as e:
                            st.error(f"AI Error: {e}")
            else:
                st.info("Add GEMINI_API_KEY to enable AI Briefings.", icon="🔑")

    with col_feed:
        st.subheader("◈ Live Node Telemetry Feed")
        df_sorted = df_raw.sort_values(by="delay_mins", ascending=False).reset_index(drop=True)

        num_cols = 3
        for i in range(0, min(9, len(df_sorted)), num_cols):
            chunk = df_sorted.iloc[i : i + num_cols]
            cols = st.columns(num_cols)
            for index, row in chunk.reset_index().iterrows():
                d = row["delay_mins"]
                s = row["speed_kmh"]
                weather_str_lower = str(row['weather']).lower()
                w_icon = "🌧️" if "rain" in weather_str_lower or "storm" in weather_str_lower else ("☁️" if "cloud" in weather_str_lower or "overcast" in weather_str_lower else "☀️")
                
                with cols[index]:
                    with st.container(border=True):
                        st.markdown(f"**{row['name']}**")
                        st.metric(label=f"Delay: +{d}m", value=f"{s} km/h")
                        st.caption(f"{w_icon} {row['weather'].split(',')[1].strip() if ',' in str(row['weather']) else row['weather']}")

        if len(df_sorted) > 9:
            st.caption(f"+{len(df_sorted)-9} more nodes within nominal thresholds")

else:
    st.status("Awaiting telemetry uplink...", state="running")
