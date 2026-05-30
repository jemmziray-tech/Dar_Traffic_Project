import os
import json
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import pytz

# --- 1. SETUP PAGE CONFIG & ENTERPRISE CSS ---
st.set_page_config(
    page_title="DarTraffic Engine",
    page_icon=":material/public:",
    layout="wide",
    initial_sidebar_state="collapsed", # Collapse sidebar for a cleaner full-screen feel
)

st.markdown("""
<style>
    /* Enterprise Typography & Layout */
    .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 98%; font-family: 'Inter', sans-serif;}
    
    /* Hero Section */
    .hero-title { font-size: 2.5rem; font-weight: 800; color: #FFFFFF; margin-bottom: 0px; letter-spacing: -0.5px;}
    .hero-subtitle { font-size: 1.1rem; color: #A0A0A0; margin-top: 5px; margin-bottom: 30px; font-weight: 400;}
    
    /* Dynamic Hover-Reactive KPI Cards */
    .kpi-card {
        background: linear-gradient(145deg, #1a1a1a 0%, #252525 100%);
        padding: 24px;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.4);
        margin-bottom: 20px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        border: 1px solid #333;
    }
    .kpi-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.6);
    }
    .kpi-title { color: #9E9E9E; font-size: 0.85rem; text-transform: uppercase; font-weight: 700; margin-bottom: 8px; letter-spacing: 1px; display: flex; align-items: center; gap: 8px;}
    .kpi-value { color: #FFFFFF; font-size: 2.4rem; font-weight: 800; margin: 0; line-height: 1.2;}
    .kpi-subtext { color: #757575; font-size: 0.85rem; margin-top: 5px;}
    
    /* Map Container styling */
    .map-container { border-radius: 12px; overflow: hidden; border: 1px solid #333; box-shadow: 0 4px 15px rgba(0,0,0,0.4); margin-top: 10px;}
    
    /* Status Pill Badges */
    .badge { padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: bold; text-transform: uppercase;}
    .badge-clear { background: rgba(0, 204, 150, 0.15); color: #00CC96; border: 1px solid #00CC96;}
    .badge-warn { background: rgba(246, 200, 95, 0.15); color: #F6C85F; border: 1px solid #F6C85F;}
    .badge-danger { background: rgba(255, 75, 75, 0.15); color: #FF4B4B; border: 1px solid #FF4B4B;}
</style>
""", unsafe_allow_html=True)


# --- 2. SECURE FIREBASE CONNECTION ---
@st.cache_resource
def get_db():
    if not firebase_admin._apps:
        # First, try to get it from Streamlit's native secrets manager
        if "FIREBASE_KEY_JSON" in st.secrets:
            # Streamlit secrets handles the JSON string directly
            firebase_secret = st.secrets["FIREBASE_KEY_JSON"]
            try:
                # If you pasted raw JSON into the secret box, parse it
                cred_dict = json.loads(firebase_secret)
                cred = credentials.Certificate(cred_dict)
            except Exception as e:
                st.error(f"Failed to parse JSON from Streamlit Secrets: {e}")
                st.stop()
        
        # Second, try standard OS environment variables (for local Docker/Render)
        elif os.getenv("FIREBASE_KEY_JSON"):
            cred_dict = json.loads(os.getenv("FIREBASE_KEY_JSON"))
            cred = credentials.Certificate(cred_dict)
            
        # Finally, fallback to local file (for local development)
        else:
            try:
                cred = credentials.Certificate("firebase-key.json")
            except Exception as e:
                st.error("CRITICAL ERROR: No Firebase credentials found in st.secrets, os.env, or local file.")
                st.stop()
                
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = get_db()

# --- 3. FETCH LIVE TELEMETRY ---
@st.cache_data(ttl=60) # Cache for 1 minute for live feel
def load_live_data():
    try:
        docs = db.collection("live_traffic").stream()
        df = pd.DataFrame([doc.to_dict() for doc in docs])
        
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values(by="timestamp", ascending=False)
            df = df.drop_duplicates(subset="road_id", keep="first")
            
        return df
    except Exception as e:
        st.error(f"Database Connection Error: {e}")
        return pd.DataFrame()

df = load_live_data()

# --- 4. HERO SECTION & HEADER ---
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.markdown('<h1 class="hero-title">:material/satellite_alt: DarTraffic Command Center</h1>', unsafe_allow_html=True)
    st.markdown('<p class="hero-subtitle">Real-time Digital Twin & AI Logistics Engine</p>', unsafe_allow_html=True)
with col_head2:
    # Live Timestamp Indicator
    if not df.empty:
        tz = pytz.timezone('Africa/Dar_es_Salaam')
        last_sync = df['timestamp'].max().astimezone(tz).strftime('%H:%M:%S EAT')
        st.markdown(f"""
        <div style="text-align: right; margin-top: 15px;">
            <span style="color: #00CC96; font-size: 0.8rem;">● LIVE TELEMETRY FEED</span><br>
            <span style="color: #A0A0A0; font-size: 0.85rem;">Last Sync: {last_sync}</span>
        </div>
        """, unsafe_allow_html=True)

if df.empty:
    st.warning(":material/sync_problem: No live telemetry found. Awaiting Cloud Scheduler sync.")
    st.stop()

# --- 5. NETWORK STATUS ALERTS ---
city_is_raining = df["weather"].str.contains("Rain", case=False, na=False).any()

if city_is_raining:
    st.error(":material/thunderstorm: **SYSTEM ADVISORY:** Rain detected in specific Dar es Salaam micro-climates. Routing algorithms automatically adjusted for elevated friction.", icon="⚠️")

# --- 6. EXECUTIVE KPI METRICS ---
avg_speed = df["speed_kmh"].mean()
worst_road_row = df.loc[df['delay_mins'].idxmax()]
worst_road_name = worst_road_row['name'].replace(' Mega-Route: ', '').split(' (')[0]
worst_road_delay = worst_road_row['delay_mins']

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <div class="kpi-card" style="border-top-color: #4B8BBE;">
        <div class="kpi-title">:material/share_location: Active Arteries Monitored</div>
        <div class="kpi-value">{len(df)}</div>
        <div class="kpi-subtext">Sensors online across major corridors</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    color = "#FF4B4B" if avg_speed < 15 else "#F6C85F" if avg_speed < 25 else "#00CC96"
    st.markdown(f"""
    <div class="kpi-card" style="border-top-color: {color};">
        <div class="kpi-title">:material/speed: City-Wide Avg Speed</div>
        <div class="kpi-value">{avg_speed:.1f} <span style="font-size: 1.2rem; color: #A0A0A0;">km/h</span></div>
        <div class="kpi-subtext">Aggregate network flow rate</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    color = "#FF4B4B" if worst_road_delay > 15 else "#F6C85F"
    st.markdown(f"""
    <div class="kpi-card" style="border-top-color: {color};">
        <div class="kpi-title">:material/warning: Primary Bottleneck</div>
        <div class="kpi-value" style="font-size: 1.8rem; margin-top: 10px;">{worst_road_name}</div>
        <div class="kpi-subtext" style="color: {color}; font-weight: bold;">+{worst_road_delay} mins structural delay</div>
    </div>
    """, unsafe_allow_html=True)


# --- 7. 4D SPATIAL MAP (FOLIUM) ---
st.markdown("<h3 style='color: #E0E0E0; font-size: 1.2rem; margin-top: 10px;'>:material/map: Spatial Telemetry Grid</h3>", unsafe_allow_html=True)

road_coords = {
    "ubungo": [-6.7978, 39.2201], "mwenge": [-6.7744, 39.2431], "selander": [-6.7950, 39.2750],
    "tazara": [-6.8288, 39.2600], "mandela_buguruni": [-6.8285, 39.2435], "kilwa_mbagala": [-6.9050, 39.2700],
    "old_bagamoyo": [-6.7720, 39.2550], "sam_nujoma": [-6.7755, 39.2435], "uhuru_street": [-6.8220, 39.2550],
    "kariakoo": [-6.8115, 39.2725], "posta_to_tegeta": [-6.7295, 39.2215], "posta_to_kimara": [-6.7980, 39.2190],
    "posta_to_gongolamboto": [-6.8505, 39.2085], "tabata_dampo": [-6.8150, 39.2320], "kamata_gerezani": [-6.8280, 39.2780],
    "changombe_road": [-6.8350, 39.2700], "morocco_intersection": [-6.7820, 39.2630], "kigogo_roundabout": [-6.8120, 39.2550],
    "fire_upanga": [-6.8120, 39.2780], "mwai_kibaki": [-6.7450, 39.2350], "sinza_mori": [-6.7780, 39.2350], "goba_massana": [-6.7250, 39.2150]
}

dar_map = folium.Map(location=[-6.81, 39.25], zoom_start=12, tiles="CartoDB dark_matter", control_scale=True)
marker_cluster = MarkerCluster().add_to(dar_map)

for idx, row in df.iterrows():
    if row["road_id"] in road_coords:
        lat, lon = road_coords[row["road_id"]]
        
        if row["status"] == "Heavy Jam" or row["delay_mins"] > 15:
            color, icon, badge_class = "red", "info-sign", "badge-danger"
            status_text = "CRITICAL GRIDLOCK"
        elif row["status"] == "Moderate" or row["delay_mins"] > 5:
            color, icon, badge_class = "orange", "info-sign", "badge-warn"
            status_text = "MODERATE FRICTION"
        else:
            color, icon, badge_class = "green", "info-sign", "badge-clear"
            status_text = "OPTIMAL FLOW"

        # Custom Dark-Mode HTML for the Popup Tooltip
        popup_html = f"""
        <div style="font-family: 'Segoe UI', sans-serif; background-color: #212121; color: #fff; padding: 15px; border-radius: 8px; min-width: 220px; border: 1px solid #444;">
            <h4 style="margin: 0 0 12px 0; font-size: 14px; color: #E0E0E0; border-bottom: 1px solid #444; padding-bottom: 8px;">{row['name']}</h4>
            <div style="margin-bottom: 12px;"><span class="badge {badge_class}">{status_text}</span></div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                <span style="color: #9e9e9e; font-size: 12px;">Delay:</span>
                <span style="font-weight: bold; color: {('#FF4B4B' if color=='red' else '#F6C85F' if color=='orange' else '#00CC96')};">+{row['delay_mins']} mins</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                <span style="color: #9e9e9e; font-size: 12px;">Speed:</span>
                <span style="font-weight: bold;">{row['speed_kmh']} km/h</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: #9e9e9e; font-size: 12px;">Weather:</span>
                <span style="font-weight: bold;">{row['weather']}</span>
            </div>
        </div>
        """

        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{row['name']} (+{row['delay_mins']}m)",
            icon=folium.Icon(color=color, icon=icon)
        ).add_to(marker_cluster)

# Render the Map inside a styled container
st.markdown('<div class="map-container">', unsafe_allow_html=True)
st_folium(dar_map, width="100%", height=550, returned_objects=[])
st.markdown('</div>', unsafe_allow_html=True)
