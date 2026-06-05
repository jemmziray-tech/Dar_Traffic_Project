import os
import json
import pandas as pd
import folium
from streamlit_folium import st_folium
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import pytz

# --- 1. SETUP PAGE CONFIG & ENTERPRISE CSS ---
st.set_page_config(
    page_title="DarTraffic Command Center",
    page_icon=":material/public:",
    layout="wide",
    initial_sidebar_state="expanded", 
)

st.markdown("""
<style>
    /* Enterprise Typography & Layout */
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 98%; font-family: 'Inter', sans-serif;}
    
    /* Hero Section */
    .hero-title { font-size: 2.5rem; font-weight: 800; color: #FFFFFF; margin-bottom: 0px; letter-spacing: -0.5px;}
    .hero-subtitle { font-size: 1.1rem; color: #A0A0A0; margin-top: 5px; margin-bottom: 25px; font-weight: 400;}
    
    /* Dynamic Hover-Reactive KPI Cards */
    .kpi-card {
        background: linear-gradient(145deg, #1a1a1a 0%, #222222 100%);
        padding: 24px;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        margin-bottom: 20px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        border: 1px solid #333;
    }
    .kpi-card:hover { transform: translateY(-5px); box-shadow: 0 8px 25px rgba(0,0,0,0.6); }
    .kpi-title { color: #9E9E9E; font-size: 0.85rem; text-transform: uppercase; font-weight: 700; margin-bottom: 8px; letter-spacing: 1px; display: flex; align-items: center; gap: 8px;}
    .kpi-value { color: #FFFFFF; font-size: 2.4rem; font-weight: 800; margin: 0; line-height: 1.2;}
    .kpi-subtext { color: #757575; font-size: 0.85rem; margin-top: 5px;}
    
    /* Map Container */
    .map-container { border-radius: 12px; overflow: hidden; border: 1px solid #333; box-shadow: 0 4px 15px rgba(0,0,0,0.4); margin-top: 10px;}
    
    /* Status Pill Badges */
    .badge { padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: bold; text-transform: uppercase;}
    .badge-clear { background: rgba(0, 204, 150, 0.15); color: #00CC96; border: 1px solid #00CC96;}
    .badge-warn { background: rgba(246, 200, 95, 0.15); color: #F6C85F; border: 1px solid #F6C85F;}
    .badge-danger { background: rgba(255, 75, 75, 0.15); color: #FF4B4B; border: 1px solid #FF4B4B;}
    
    /* Architect Signature Badge */
    .architect-badge {
        background-color: #121212;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 8px;
        margin-top: 50px;
        text-align: center;
    }
    .architect-name { color: #FFFFFF; font-weight: bold; font-size: 1.1rem;}
    .architect-title { color: #4B8BBE; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;}
</style>
""", unsafe_allow_html=True)

# --- 2. SIDEBAR (ARCHITECT SIGNATURE) ---
with st.sidebar:
    st.markdown("""
    <div class="architect-badge">
        <div style="color: #A0A0A0; font-size: 0.8rem; margin-bottom: 5px;">SYSTEM ARCHITECT</div>
        <div class="architect-name">John Mziray</div>
        <div class="architect-title">BSc in AI & Machine Learning</div>
    </div>
    """, unsafe_allow_html=True)

# --- 3. SECURE FIREBASE CONNECTION ---
@st.cache_resource
def get_db():
    if not firebase_admin._apps:
        if os.path.exists("firebase-key.json"):
            cred = credentials.Certificate("firebase-key.json")
        elif "firebase" in st.secrets:
            key_dict = json.loads(st.secrets["firebase"]["key_data"]) if "key_data" in st.secrets["firebase"] else dict(st.secrets["firebase"])
            cred = credentials.Certificate(key_dict)
        elif os.getenv("FIREBASE_KEY_JSON"):
            cred = credentials.Certificate(json.loads(os.getenv("FIREBASE_KEY_JSON")))
        else:
            st.error("Authentication Failure: No Firebase credentials found.")
            st.stop()
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = get_db()

# --- 4. FETCH LIVE TELEMETRY (PURE PRODUCTION DATA) ---
@st.cache_data(ttl=60) 
def load_live_data():
    try:
        docs = db.collection("live_traffic").stream()
        df = pd.DataFrame([doc.to_dict() for doc in docs])
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            # Keep only the absolute freshest ping for each road
            df = df.sort_values(by="timestamp", ascending=False).drop_duplicates(subset="road_id", keep="first")
        return df
    except Exception as e:
        st.error(f"Database Connection Error: {e}")
        return pd.DataFrame()

df = load_live_data()

# --- 5. HERO SECTION ---
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.markdown('<h1 class="hero-title">:material/satellite_alt: DarTraffic Command Center</h1>', unsafe_allow_html=True)
    st.markdown('<p class="hero-subtitle">Real-time Digital Twin & AI Logistics Engine</p>', unsafe_allow_html=True)
with col_head2:
    if not df.empty:
        tz = pytz.timezone('Africa/Dar_es_Salaam')
        last_sync = df['timestamp'].max().astimezone(tz).strftime('%H:%M:%S EAT')
        st.markdown(f"""
        <div style="text-align: right; margin-top: 15px;">
            <span style="color: #00CC96; font-size: 0.8rem; font-weight: bold;">● LIVE SENSOR FEED</span><br>
            <span style="color: #A0A0A0; font-size: 0.85rem;">Last Sync: {last_sync}</span>
        </div>
        """, unsafe_allow_html=True)

if df.empty:
    st.warning(":material/sync_problem: No live telemetry found. Awaiting Cloud Scheduler sync.")
    st.stop()

# --- 6. NETWORK ALERTS ---
if df["weather"].str.contains("Rain", case=False, na=False).any():
    st.error(":material/thunderstorm: **WEATHER ADVISORY:** Precipitation detected in specific Dar es Salaam micro-climates. Routing algorithms adjusting for elevated friction.", icon="⚠️")

# --- 7. EXECUTIVE KPI METRICS ---
avg_speed = df["speed_kmh"].mean()
worst_road_row = df.loc[df['delay_mins'].idxmax()]
worst_road_name = worst_road_row['name'].replace('Mega-Route: ', '').split(' (')[0]
worst_road_delay = worst_road_row['delay_mins']

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <div class="kpi-card" style="border-top-color: #4B8BBE;">
        <div class="kpi-title">:material/sensors: Active Arteries Monitored</div>
        <div class="kpi-value">{len(df)}</div>
        <div class="kpi-subtext">Sensors online across major corridors</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    color = "#FF4B4B" if avg_speed < 15 else "#F6C85F" if avg_speed < 25 else "#00CC96"
    st.markdown(f"""
    <div class="kpi-card" style="border-top-color: {color};">
        <div class="kpi-title">:material/speed: City-Wide Average Velocity</div>
        <div class="kpi-value">{avg_speed:.1f} <span style="font-size: 1.2rem; color: #A0A0A0;">km/h</span></div>
        <div class="kpi-subtext">Aggregate network flow rate</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    color = "#FF4B4B" if worst_road_delay > 15 else "#F6C85F"
    st.markdown(f"""
    <div class="kpi-card" style="border-top-color: {color};">
        <div class="kpi-title">:material/warning: Primary Congestion Point</div>
        <div class="kpi-value" style="font-size: 1.8rem; margin-top: 10px;">{worst_road_name}</div>
        <div class="kpi-subtext" style="color: {color}; font-weight: bold;">+{worst_road_delay} mins structural delay</div>
    </div>
    """, unsafe_allow_html=True)


# --- 8. THE HIDDEN 4D SPATIAL MAP ---
with st.expander(":material/map: Expand Spatial Telemetry Grid (Map View)", expanded=False):
    st.markdown("<p style='color: #A0A0A0; font-size: 0.9rem; margin-bottom: 15px;'>Interactive geospatial visualization of real-time Dar es Salaam structural bottlenecks.</p>", unsafe_allow_html=True)

    road_segments = {
        "ubungo": [[-6.7978,39.2201], [-6.8040,39.2300]],
        "mwenge": [[-6.7744,39.2431], [-6.7631,39.2489]],
        "selander": [[-6.7950,39.2750], [-6.8050,39.2850]],
        "tazara": [[-6.8288,39.2600], [-6.8400,39.2480]],
        "mandela_buguruni": [[-6.8285,39.2435], [-6.8335,39.2620]],
        "kilwa_mbagala": [[-6.9050,39.2700], [-6.8750,39.2800]],
        "old_bagamoyo": [[-6.7720,39.2550], [-6.7820,39.2650]],
        "sam_nujoma": [[-6.7755,39.2435], [-6.7975,39.2205]],
        "uhuru_street": [[-6.8220,39.2550], [-6.8155,39.2820]],
        "kariakoo": [[-6.8115,39.2725], [-6.8210,39.2750]],
        "posta_to_tegeta": [[-6.8160,39.2880], [-6.6430,39.1550]],
        "posta_to_kimara": [[-6.8160,39.2880], [-6.7800,39.1500]],
        "posta_to_gongolamboto": [[-6.8160,39.2880], [-6.8850,39.1670]],
        "tabata_dampo": [[-6.8150,39.2320], [-6.8300,39.2050]],
        "kamata_gerezani": [[-6.8280,39.2780], [-6.8180,39.2850]],
        "changombe_road": [[-6.8350,39.2700], [-6.8550,39.2650]],
        "morocco_intersection": [[-6.7820,39.2630], [-6.7950,39.2580]],
        "kigogo_roundabout": [[-6.8120,39.2550], [-6.8220,39.2500]],
        "fire_upanga": [[-6.8120,39.2780], [-6.8020,39.2720]],
        "mwai_kibaki": [[-6.7450,39.2350], [-6.7650,39.2500]],
        "sinza_mori": [[-6.7780,39.2350], [-6.7700,39.2450]],
        "goba_massana": [[-6.7250,39.2150], [-6.7150,39.1850]]
    }

    dar_map = folium.Map(location=[-6.815, 39.255], zoom_start=12, tiles="CartoDB dark_matter", control_scale=True)

    for idx, row in df.iterrows():
        if row["road_id"] in road_segments:
            coords = road_segments[row["road_id"]]
            center_lat = (coords[0][0] + coords[1][0]) / 2
            center_lon = (coords[0][1] + coords[1][1]) / 2
            
            if row["status"] == "Heavy Jam" or row["delay_mins"] > 15:
                hex_color, badge_class = "#FF4B4B", "badge-danger"
                status_text, map_weight = "CRITICAL GRIDLOCK", 6
            elif row["status"] == "Moderate" or row["delay_mins"] > 5:
                hex_color, badge_class = "#F6C85F", "badge-warn"
                status_text, map_weight = "MODERATE FRICTION", 4
            else:
                hex_color, badge_class = "#00CC96", "badge-clear"
                status_text, map_weight = "OPTIMAL FLOW", 3

            popup_html = f"""
            <div style="font-family: 'Segoe UI', sans-serif; background-color: #212121; color: #fff; padding: 15px; border-radius: 8px; min-width: 220px; border: 1px solid #444;">
                <h4 style="margin: 0 0 12px 0; font-size: 14px; color: #E0E0E0; border-bottom: 1px solid #444; padding-bottom: 8px;">{row['name']}</h4>
                <div style="margin-bottom: 12px;"><span class="badge {badge_class}">{status_text}</span></div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                    <span style="color: #9e9e9e; font-size: 12px;">Delay:</span>
                    <span style="font-weight: bold; color: {hex_color};">+{row['delay_mins']} mins</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                    <span style="color: #9e9e9e; font-size: 12px;">Live Speed:</span>
                    <span style="font-weight: bold;">{row['speed_kmh']} km/h</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #9e9e9e; font-size: 12px;">Weather:</span>
                    <span style="font-weight: bold;">{row['weather']}</span>
                </div>
            </div>
            """

            folium.PolyLine(locations=coords, color=hex_color, weight=map_weight, opacity=0.8, tooltip=f"{row['name']} (+{row['delay_mins']}m)").add_to(dar_map)
            folium.CircleMarker(location=[center_lat, center_lon], radius=4, color=hex_color, fill=True, fill_color=hex_color, fill_opacity=1.0, popup=folium.Popup(popup_html, max_width=300)).add_to(dar_map)

    st.markdown('<div class="map-container">', unsafe_allow_html=True)
    st_folium(dar_map, width="100%", height=600, returned_objects=[])
    st.markdown('</div>', unsafe_allow_html=True)
