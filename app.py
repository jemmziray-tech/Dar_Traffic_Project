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
    page_title="DarTraffic Command",
    page_icon=":material/public:",
    layout="wide",
    initial_sidebar_state="expanded", 
)

st.markdown("""
<style>
    /* Enterprise Typography & Layout */
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 98%; font-family: 'Inter', sans-serif;}
    
    /* Hero Section */
    .hero-title { font-size: 2.8rem; font-weight: 900; color: #FFFFFF; margin-bottom: 0px; letter-spacing: -1px;}
    .hero-subtitle { font-size: 1.1rem; color: #A0A0A0; margin-top: 5px; margin-bottom: 25px; font-weight: 500; text-transform: uppercase; letter-spacing: 1.5px;}
    
    /* Dynamic Hover-Reactive KPI Cards */
    .kpi-card {
        background: linear-gradient(145deg, #161616 0%, #1e1e1e 100%);
        padding: 24px;
        border-radius: 10px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        margin-bottom: 20px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        border: 1px solid #2a2a2a;
    }
    .kpi-card:hover { transform: translateY(-4px); box-shadow: 0 8px 30px rgba(0,0,0,0.7); border-color: #444;}
    .kpi-title { color: #888888; font-size: 0.8rem; text-transform: uppercase; font-weight: 700; margin-bottom: 12px; letter-spacing: 1px; display: flex; align-items: center; gap: 8px;}
    .kpi-value { color: #FFFFFF; font-size: 2.6rem; font-weight: 900; margin: 0; line-height: 1.1; font-family: 'Courier New', monospace;}
    .kpi-subtext { color: #666666; font-size: 0.8rem; margin-top: 8px; font-weight: 600;}
    
    /* Glowing Map Container */
    .map-container { 
        border-radius: 12px; 
        overflow: hidden; 
        border: 1px solid #333; 
        box-shadow: 0 0 20px rgba(0, 204, 150, 0.1); 
        margin-top: 10px;
    }
    
    /* Status Pill Badges */
    .badge { padding: 5px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px;}
    .badge-clear { background: rgba(0, 204, 150, 0.15); color: #00CC96; border: 1px solid rgba(0, 204, 150, 0.4);}
    .badge-warn { background: rgba(246, 200, 95, 0.15); color: #F6C85F; border: 1px solid rgba(246, 200, 95, 0.4);}
    .badge-danger { background: rgba(255, 75, 75, 0.15); color: #FF4B4B; border: 1px solid rgba(255, 75, 75, 0.4);}
    
    /* Architect Signature Badge */
    .architect-badge {
        background: linear-gradient(to bottom right, #1a1a1a, #0d0d0d);
        border: 1px solid #333;
        padding: 18px;
        border-radius: 10px;
        margin-top: 40px;
        text-align: center;
        box-shadow: inset 0 0 15px rgba(0,0,0,0.8);
    }
    .architect-name { color: #E0E0E0; font-weight: 900; font-size: 1.2rem; letter-spacing: 0.5px;}
    .architect-title { color: #4B8BBE; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; margin-top: 4px;}
</style>
""", unsafe_allow_html=True)

# --- 2. SIDEBAR (ARCHITECT SIGNATURE) ---
with st.sidebar:
    st.markdown("""
    <div class="architect-badge">
        <div style="color: #666; font-size: 0.7rem; margin-bottom: 8px; font-weight: bold; letter-spacing: 2px;">LEAD SYSTEM ARCHITECT</div>
        <div class="architect-name">John Mziray</div>
        <div class="architect-title">B.Sc. Artificial Intelligence</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    # The toggle now controls whether we filter the map down to the Top 10 worst routes.
    focus_top_10 = st.toggle("Isolate Top 10 Bottlenecks", True, help="Automatically isolates and maps the 10 worst live gridlocks in the city.")

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

# --- 4. FETCH LIVE TELEMETRY ---
@st.cache_data(ttl=60) 
def load_live_data():
    try:
        docs = db.collection("live_traffic").stream()
        df = pd.DataFrame([doc.to_dict() for doc in docs])
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values(by="timestamp", ascending=False).drop_duplicates(subset="road_id", keep="first")
        return df
    except Exception as e:
        st.error(f"Database Connection Error: {e}")
        return pd.DataFrame()

# We call the raw data once
df = load_live_data()

# --- 5. DYNAMIC TARGETING (THE AUTOMATION) ---
if not df.empty and focus_top_10:
    # Ask Pandas to sort the whole dataframe by delay, and give us a list of the top 10 road IDs
    top_10_roads = df.sort_values(by="delay_mins", ascending=False).head(10)["road_id"].tolist()
else:
    # If the toggle is off, or the DB is small, map everything
    top_10_roads = df["road_id"].tolist() if not df.empty else []


# --- 6. HERO SECTION ---
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.markdown('<h1 class="hero-title">:material/satellite_alt: FLOWTRACK ORACLE</h1>', unsafe_allow_html=True)
    st.markdown('<p class="hero-subtitle">Dar es Salaam Predictive Logistics Engine</p>', unsafe_allow_html=True)
with col_head2:
    if not df.empty:
        tz = pytz.timezone('Africa/Dar_es_Salaam')
        last_sync = df['timestamp'].max().astimezone(tz).strftime('%H:%M:%S EAT')
        st.markdown(f"""
        <div style="text-align: right; margin-top: 15px; background: rgba(0,204,150,0.1); padding: 10px; border-radius: 8px; border: 1px solid rgba(0,204,150,0.3); display: inline-block; float: right;">
            <span style="color: #00CC96; font-size: 0.75rem; font-weight: 800; letter-spacing: 1px;">● SECURE SENSOR UPLINK</span><br>
            <span style="color: #A0A0A0; font-size: 0.85rem; font-family: monospace;">T= {last_sync}</span>
        </div>
        """, unsafe_allow_html=True)

if df.empty:
    st.warning(":material/sync_problem: Core systems awaiting telemetry uplink.")
    st.stop()

# --- 7. EXECUTIVE KPI METRICS ---
avg_speed = df["speed_kmh"].mean()
worst_road_row = df.loc[df['delay_mins'].idxmax()]
worst_road_name = worst_road_row['name'].replace('Mega-Route: ', '').split(' (')[0]
worst_road_delay = worst_road_row['delay_mins']

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <div class="kpi-card" style="border-top-color: #4B8BBE; border-top-width: 3px;">
        <div class="kpi-title">:material/network_node: Active Nodes</div>
        <div class="kpi-value">{len(df)} <span style="font-size: 1.2rem; color: #555;">units</span></div>
        <div class="kpi-subtext">Spatial grid fully operational</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    color = "#FF4B4B" if avg_speed < 15 else "#F6C85F" if avg_speed < 25 else "#00CC96"
    st.markdown(f"""
    <div class="kpi-card" style="border-top-color: {color}; border-top-width: 3px;">
        <div class="kpi-title">:material/speed: Network Velocity</div>
        <div class="kpi-value">{avg_speed:.1f} <span style="font-size: 1.2rem; color: #555;">km/h</span></div>
        <div class="kpi-subtext">Aggregate fleet flow rate</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    color = "#FF4B4B" if worst_road_delay > 15 else "#F6C85F"
    st.markdown(f"""
    <div class="kpi-card" style="border-top-color: {color}; border-top-width: 3px;">
        <div class="kpi-title">:material/warning: Structural Bottleneck</div>
        <div class="kpi-value" style="font-size: 1.6rem; margin-top: 5px; font-family: 'Inter', sans-serif;">{worst_road_name}</div>
        <div class="kpi-subtext" style="color: {color};">+{worst_road_delay} min absolute delay margin</div>
    </div>
    """, unsafe_allow_html=True)


# --- 8. 4D SPATIAL MAP (LINES & MARKERS) ---
st.markdown("<h3 style='color: #E0E0E0; font-size: 1.2rem; margin-top: 15px; margin-bottom: 5px; font-weight: 800; letter-spacing: 0.5px;'>:material/map: CITY-WIDE TELEMETRY GRID</h3>", unsafe_allow_html=True)

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

# Loop through the database, but ONLY plot the roads that made the dynamically calculated Top 10 List!
for idx, row in df.iterrows():
    if row["road_id"] in road_segments and row["road_id"] in top_10_roads:
        coords = road_segments[row["road_id"]]
        center_lat = (coords[0][0] + coords[1][0]) / 2
        center_lon = (coords[0][1] + coords[1][1]) / 2
        
        # Color based on ACTUAL live delay in the database
        if row["status"] == "Heavy Jam" or row["delay_mins"] >= 15:
            hex_color, badge_class = "#FF3333", "badge-danger"
            status_text, map_weight = "SEVERE GRIDLOCK", 6
        elif row["status"] == "Moderate" or row["delay_mins"] >= 5:
            hex_color, badge_class = "#FFAA00", "badge-warn"
            status_text, map_weight = "MODERATE FRICTION", 4
        else:
            hex_color, badge_class = "#00CC96", "badge-clear"
            status_text, map_weight = "OPTIMAL FLOW", 3

        popup_html = f"""
        <div style="font-family: 'Segoe UI', sans-serif; background-color: #1a1a1a; color: #fff; padding: 16px; border-radius: 6px; min-width: 220px; border: 1px solid #333; box-shadow: 0 4px 15px rgba(0,0,0,0.5);">
            <h4 style="margin: 0 0 12px 0; font-size: 14px; font-weight: 800; color: #FFF; border-bottom: 1px solid #333; padding-bottom: 8px; text-transform: uppercase;">{row['name']}</h4>
            <div style="margin-bottom: 14px;"><span class="badge {badge_class}">{status_text}</span></div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span style="color: #888; font-size: 11px; text-transform: uppercase; font-weight: bold;">Structural Delay:</span>
                <span style="font-weight: 900; font-size: 14px; color: {hex_color};">+{row['delay_mins']} mins</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span style="color: #888; font-size: 11px; text-transform: uppercase; font-weight: bold;">Telemetry Speed:</span>
                <span style="font-weight: 900; font-size: 14px;">{row['speed_kmh']} km/h</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: #888; font-size: 11px; text-transform: uppercase; font-weight: bold;">Micro-Climate:</span>
                <span style="font-weight: 900; font-size: 14px;">{row['weather']}</span>
            </div>
        </div>
        """

        tooltip_html = f"<div style='font-family: monospace; font-weight: bold;'>{row['name']}<br>Delay: +{row['delay_mins']}m</div>"

        folium.PolyLine(locations=coords, color=hex_color, weight=map_weight, opacity=0.9, tooltip=tooltip_html).add_to(dar_map)
        folium.CircleMarker(location=[center_lat, center_lon], radius=4, color=hex_color, fill=True, fill_color=hex_color, fill_opacity=1.0, popup=folium.Popup(popup_html, max_width=300)).add_to(dar_map)

st.markdown('<div class="map-container">', unsafe_allow_html=True)
st_folium(dar_map, width="100%", height=650, returned_objects=[])
st.markdown('</div>', unsafe_allow_html=True)
