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
import google.generativeai as genai

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="FlowTrack Enterprise | Dar es Salaam",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Subtle, clean CSS to tighten the layout and make it feel like a seamless app
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 95%; }
    header {visibility: hidden;} /* Hides the default Streamlit top bar */
    .stMetric { background-color: #161616; padding: 15px; border-radius: 8px; border: 1px solid #2a2a2a; }
</style>
""", unsafe_allow_html=True)

# --- 2. FIREBASE CONNECTION ---
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
            st.error("Authentication Failure: System cannot locate Firebase credentials.")
            st.stop()
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = get_db()

# --- 3. DATA INGESTION ---
@st.cache_data(ttl=60)
def load_live_data():
    try:
        docs = db.collection("live_traffic").stream()
        df = pd.DataFrame([doc.to_dict() for doc in docs])
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values(by="timestamp", ascending=False).drop_duplicates(subset="road_id", keep="first")
            df = df.sort_values(by="delay_mins", ascending=False).reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"Telemetry Error: {e}")
        return pd.DataFrame()

df = load_live_data()

# --- 4. HEADER SECTION ---
c1, c2 = st.columns([3, 1])
with c1:
    st.title("FlowTrack Enterprise")
    st.caption("Dar es Salaam Predictive Logistics & Telemetry Engine // Lead Architect: John Mziray")
with c2:
    if not df.empty:
        tz = pytz.timezone('Africa/Dar_es_Salaam')
        last_sync = df['timestamp'].max().astimezone(tz).strftime('%H:%M:%S EAT')
        st.success(f"🟢 **SECURE UPLINK ACTIVE** | T= {last_sync}")
    else:
        st.warning("🟡 **SYSTEM IDLE** | Awaiting Telemetry")
        st.stop()

st.divider()

# --- 5. TOP LEVEL KPIs ---
avg_speed = df["speed_kmh"].mean()
worst_road = df.iloc[0]
total_delay = df["delay_mins"].sum()

m1, m2, m3, m4 = st.columns(4)
m1.metric(label="Monitored Corridors", value=len(df), delta="Spatial Grid Online")
m2.metric(label="Network Velocity", value=f"{avg_speed:.1f} km/h", delta="City-wide average")
m3.metric(label="Cumulative Friction", value=f"{total_delay} mins", delta="Total network delay", delta_color="inverse")
m4.metric(label="Primary Bottleneck", value=worst_road['name'].replace('Mega-Route: ', '').split(' (')[0], delta=f"+{worst_road['delay_mins']} mins", delta_color="inverse")

st.write("") # Spacer

# --- 6. GEOSPATIAL MAP (HERO ELEMENT) ---
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
        
        # Elegant data-driven styling
        if row["delay_mins"] > 15:
            color, weight, opacity = "#FF4B4B", 6, 0.9 # Thick Red
        elif row["delay_mins"] > 5:
            color, weight, opacity = "#F6C85F", 4, 0.7 # Medium Yellow
        else:
            color, weight, opacity = "#00CC96", 2, 0.4 # Thin Green
            
        tooltip = f"<span style='font-family: sans-serif;'><b>{row['name']}</b><br>Delay: +{row['delay_mins']}m | Speed: {row['speed_kmh']}km/h</span>"
        folium.PolyLine(locations=coords, color=color, weight=weight, opacity=opacity, tooltip=tooltip).add_to(dar_map)

# Render map spanning full width
st_folium(dar_map, use_container_width=True, height=500, returned_objects=[])

st.write("")

# --- 7. ANALYSIS & DATA FEED ---
col_ai, col_data = st.columns([1, 2], gap="large")

with col_ai:
    st.subheader("🤖 AI Dispatch Oracle")
    st.caption("Live macro-analysis generated by Gemini 3.5")
    with st.container(border=True):
        gemini_key = os.getenv("GEMINI_API_KEY") or (st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else None)
        
        if gemini_key:
            genai.configure(api_key=gemini_key)
            if st.button("Request Tactical Briefing", use_container_width=True):
                with st.spinner("Analyzing telemetry..."):
                    try:
                        prompt = f"You are a logistics AI for Dar es Salaam. Network avg speed is {avg_speed:.1f}km/h. Worst road is {worst_road['name']} with {worst_road['delay_mins']} min delay. Write a 3-sentence executive summary for commercial fleets advising them on current routing conditions. Be highly professional. No markdown."
                        response = genai.GenerativeModel("gemini-3.5-flash").generate_content(prompt)
                        st.info(response.text)
                    except Exception as e:
                        st.error(f"API Error: {e}")
        else:
            st.info("System requires Gemini API key to generate briefings.")

with col_data:
    st.subheader("📊 Live Corridor Telemetry")
    st.caption("Real-time network node parameters, sorted by severity")
    
    # Create a clean, elegant dataframe
    display_df = df[['name', 'delay_mins', 'speed_kmh', 'weather', 'status']].copy()
    display_df.columns = ['Route Corridor', 'Delay (Mins)', 'Velocity (km/h)', 'Micro-Climate', 'Status']
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=300,
        column_config={
            "Delay (Mins)": st.column_config.ProgressColumn("Delay (Mins)", format="%d", min_value=0, max_value=60),
            "Velocity (km/h)": st.column_config.NumberColumn("Velocity (km/h)", format="%.1f"),
            "Status": st.column_config.TextColumn("Status")
        }
    )
