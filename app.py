import os
import json
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
from config import ROAD_COORDS, ROAD_PATHS

# --- 1. Setup Page Config ---
st.set_page_config(
    page_title="Dar Traffic Command",
    layout="wide",
    page_icon=":material/satellite_alt:",
    initial_sidebar_state="expanded",
)

# --- PREMIUM DESIGN SYSTEM CSS ---
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Inter', sans-serif !important;
    background-color: #0A0F1E;
    color: #E8EAF0;
}

/* --- Sidebar --- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0D1426 0%, #0A0F1E 100%) !important;
    border-right: 1px solid rgba(0, 212, 255, 0.1);
}
[data-testid="stSidebar"] * { font-family: 'Inter', sans-serif !important; }

/* --- Main container padding --- */
.block-container { padding-top: 1.8rem; padding-bottom: 2rem; max-width: 98%; }

/* --- Metric values --- */
div[data-testid="stMetricValue"] {
    font-weight: 700;
    font-size: 1.6rem !important;
    letter-spacing: -0.5px;
    color: #FFFFFF;
}
div[data-testid="stMetricLabel"] { color: #8892A4 !important; font-size: 0.78rem; font-weight: 500; letter-spacing: 0.5px; text-transform: uppercase; }

/* --- KPI card glow --- */
.kpi-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(0, 212, 255, 0.15);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    transition: border-color 0.3s, box-shadow 0.3s;
}
.kpi-card:hover { border-color: rgba(0, 212, 255, 0.4); box-shadow: 0 0 20px rgba(0, 212, 255, 0.08); }

/* --- Road telemetry cards --- */
.road-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 2px;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s, box-shadow 0.2s;
}
.road-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.3); }
.road-card::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 3px;
    border-radius: 10px 0 0 10px;
}
.road-card.smooth::before { background: #2ED573; box-shadow: 0 0 8px rgba(46,213,115,0.6); }
.road-card.moderate::before { background: #FFA502; box-shadow: 0 0 8px rgba(255,165,2,0.6); }
.road-card.jammed::before { background: #FF4757; box-shadow: 0 0 8px rgba(255,71,87,0.6); }

.road-name { font-size: 0.72rem; font-weight: 600; color: #8892A4; letter-spacing: 0.8px; text-transform: uppercase; margin-bottom: 6px; }
.road-speed { font-size: 1.5rem; font-weight: 800; color: #FFFFFF; line-height: 1.1; }
.road-speed span { font-size: 0.75rem; font-weight: 400; color: #8892A4; }
.delay-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 600;
    margin-top: 6px;
}
.delay-badge.smooth { background: rgba(46,213,115,0.12); color: #2ED573; border: 1px solid rgba(46,213,115,0.3); }
.delay-badge.moderate { background: rgba(255,165,2,0.12); color: #FFA502; border: 1px solid rgba(255,165,2,0.3); }
.delay-badge.jammed { background: rgba(255,71,87,0.12); color: #FF4757; border: 1px solid rgba(255,71,87,0.3); }

.weather-tag { font-size: 0.68rem; color: #5C6680; margin-top: 4px; }
.speed-bar-bg { background: rgba(255,255,255,0.06); border-radius: 4px; height: 4px; margin-top: 8px; overflow: hidden; }
.speed-bar-fill { height: 4px; border-radius: 4px; transition: width 0.5s ease; }

/* --- Section headers --- */
.section-header { font-size: 0.72rem; font-weight: 600; color: #00D4FF; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 12px; }

/* --- Pulsing live dot --- */
.blob { border-radius: 50%; margin-right: 8px; height: 10px; width: 10px; display: inline-block; }
.blob.green { background: #2ED573; box-shadow: 0 0 8px rgba(46,213,115,0.8); animation: pulse 2s infinite; }
.blob.yellow { background: #FFA502; box-shadow: 0 0 8px rgba(255,165,2,0.8); }
.blob.red { background: #FF4757; box-shadow: 0 0 8px rgba(255,71,87,0.8); }
@keyframes pulse {
    0%   { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(46,213,115,0.7); }
    70%  { transform: scale(1);    box-shadow: 0 0 0 10px rgba(46,213,115,0); }
    100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(46,213,115,0); }
}

/* --- Buttons --- */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    transition: all 0.2s !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #00D4FF, #0099CC) !important;
    border: none !important;
    color: #0A0F1E !important;
}
.stButton > button[kind="primary"]:hover { box-shadow: 0 0 20px rgba(0,212,255,0.4) !important; }

/* --- Network status card --- */
.net-status-card {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 18px;
}

/* --- Hero title --- */
.hero-title { font-size: 2rem; font-weight: 800; color: #FFFFFF; letter-spacing: -1px; line-height: 1.2; }
.hero-sub { font-size: 0.85rem; color: #5C6680; font-weight: 400; margin-top: 4px; }
.live-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(46,213,115,0.1); border: 1px solid rgba(46,213,115,0.25);
    color: #2ED573; font-size: 0.72rem; font-weight: 600;
    padding: 4px 10px; border-radius: 20px; letter-spacing: 0.5px;
}
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
# (Imported dynamically from config.py to ensure zero redundancy)


# --- 4. Helper Functions ---
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

    # Hero header
    h1, h2 = st.columns([3, 1])
    with h1:
        st.markdown(f"""
        <div class="hero-title">Dar es Salaam Traffic Command</div>
        <div class="hero-sub">Smart City Digital Twin — Real-Time Infrastructure Intelligence</div>
        """, unsafe_allow_html=True)
    with h2:
        st.markdown(f"""
        <div style="text-align:right; padding-top: 8px;">
            <span class="live-badge"><span style="width:7px;height:7px;background:#2ED573;border-radius:50%;display:inline-block;"></span> LIVE NETWORK</span>
            <div style="font-size:0.75rem; color:#5C6680; margin-top:4px;">{datetime.now(tz).strftime('%H:%M %Z · %d %b %Y')}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:20px'></div>", unsafe_allow_html=True)

    # Premium KPI row
    friction_str = f"{total_wasted_tzs/1000000:.1f}M TZS" if total_wasted_tzs >= 1000000 else f"{total_wasted_tzs:,.0f} TZS"
    eff_color = "#2ED573" if efficiency > 70 else ("#FFA502" if efficiency > 40 else "#FF4757")
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f"""<div class="kpi-card">
        <div style="font-size:0.7rem;color:#8892A4;text-transform:uppercase;letter-spacing:1px;font-weight:600;">Network Efficiency</div>
        <div style="font-size:2rem;font-weight:800;color:{eff_color};margin:6px 0;">{efficiency:.1f}%</div>
        <div style="font-size:0.72rem;color:#5C6680;">{'Optimal Flow' if efficiency > 70 else ('Moderate Stress' if efficiency > 40 else 'Critical Load')}</div>
    </div>""", unsafe_allow_html=True)
    k2.markdown(f"""<div class="kpi-card">
        <div style="font-size:0.7rem;color:#8892A4;text-transform:uppercase;letter-spacing:1px;font-weight:600;">Average Velocity</div>
        <div style="font-size:2rem;font-weight:800;color:#00D4FF;margin:6px 0;">{avg_speed:.1f} <span style='font-size:1rem;color:#5C6680;'>km/h</span></div>
        <div style="font-size:0.72rem;color:#5C6680;">City-wide mean speed</div>
    </div>""", unsafe_allow_html=True)
    k3.markdown(f"""<div class="kpi-card">
        <div style="font-size:0.7rem;color:#8892A4;text-transform:uppercase;letter-spacing:1px;font-weight:600;">Cumulative Gridlock</div>
        <div style="font-size:2rem;font-weight:800;color:#FFA502;margin:6px 0;">{total_delay} <span style='font-size:1rem;color:#5C6680;'>mins</span></div>
        <div style="font-size:0.72rem;color:#5C6680;">Across all corridors</div>
    </div>""", unsafe_allow_html=True)
    k4.markdown(f"""<div class="kpi-card">
        <div style="font-size:0.7rem;color:#8892A4;text-transform:uppercase;letter-spacing:1px;font-weight:600;">Capital Friction</div>
        <div style="font-size:2rem;font-weight:800;color:#FF4757;margin:6px 0;">{friction_str}</div>
        <div style="font-size:0.72rem;color:#5C6680;">Wasted productivity</div>
    </div>""", unsafe_allow_html=True)

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
        # Network Status
        bottleneck_row = df_raw.loc[df_raw["delay_mins"].idxmax()]
        if total_delay > 150:
            status_icon, status_color, status_label = "⚠️", "#FF4757", f"Critical congestion on {bottleneck_row['name']}"
        elif "Rain" in str(df_raw["weather"].iloc[0]) or "Drizzle" in str(df_raw["weather"].iloc[0]):
            status_icon, status_color, status_label = "🌧️", "#FFA502", "Precipitation detected — speeds reduced"
        else:
            status_icon, status_color, status_label = "✅", "#2ED573", "All arteries flowing nominally"

        eff_bar_pct = int(efficiency)
        st.markdown(f"""
        <div class="net-status-card" style="margin-bottom:16px;">
            <div style="font-size:0.7rem;color:#8892A4;text-transform:uppercase;letter-spacing:1px;font-weight:600;margin-bottom:10px;">⬡ Network Status</div>
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
                <span style="font-size:1.4rem;">{status_icon}</span>
                <div>
                    <div style="font-size:0.85rem;font-weight:600;color:{status_color};">{status_label}</div>
                    <div style="font-size:0.72rem;color:#5C6680;">Structural Efficiency: {efficiency:.1f}%</div>
                </div>
            </div>
            <div style="background:rgba(255,255,255,0.06);border-radius:6px;height:6px;overflow:hidden;">
                <div style="width:{eff_bar_pct}%;height:6px;background:linear-gradient(90deg,{status_color},{status_color}88);border-radius:6px;"></div>
            </div>
            <div style="font-size:0.7rem;color:#5C6680;margin-top:8px;">Worst: <span style='color:#FF4757;font-weight:600;'>{bottleneck_row['name']}</span> (+{bottleneck_row['delay_mins']} mins)</div>
        </div>
        """, unsafe_allow_html=True)

        # AI Briefing
        st.markdown('<div class="net-status-card">', unsafe_allow_html=True)
        st.markdown('<div style="font-size:0.7rem;color:#8892A4;text-transform:uppercase;letter-spacing:1px;font-weight:600;margin-bottom:10px;">🤖 AI Executive Briefing</div>', unsafe_allow_html=True)
        st.caption("Live macro-summary for logistics & fleet planning.")
        gemini_key = os.getenv("GEMINI_API_KEY") or (
            st.secrets.get("GEMINI_API_KEY")
            if "GEMINI_API_KEY" in st.secrets
            else None
        )
        if gemini_key:
            genai.configure(api_key=gemini_key)
            if st.button("Generate Dispatch Report", type="primary", use_container_width=True, icon=":material/graphic_eq:"):
                with st.spinner("Analyzing macro-level routing data..."):
                    try:
                        prompt = f"You are a logistics AI for Dar es Salaam. Flow is {efficiency:.1f}%. Worst road is {bottleneck_row['name']} with {bottleneck_row['delay_mins']} min delay. Write a 3-sentence professional executive summary for commercial fleets in native swahili advising them on current conditions. No markdown."
                        response = genai.GenerativeModel("gemini-2.0-flash").generate_content(prompt)
                        st.markdown(f'<div style="background:rgba(0,212,255,0.05);border:1px solid rgba(0,212,255,0.2);border-radius:8px;padding:12px;font-size:0.85rem;color:#C8D0E0;line-height:1.6;margin-top:10px;">{response.text}</div>', unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"AI Error: {e}")
        else:
            st.info("Add GEMINI_API_KEY to enable AI Briefings.", icon=":material/key:")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_feed:
        st.markdown('<div class="section-header">◈ Live Node Telemetry Feed</div>', unsafe_allow_html=True)
        df_sorted = df_raw.sort_values(by="delay_mins", ascending=False).reset_index(drop=True)

        num_cols = 3
        for i in range(0, min(9, len(df_sorted)), num_cols):
            chunk = df_sorted.iloc[i : i + num_cols]
            cols = st.columns(num_cols)
            for index, row in chunk.reset_index().iterrows():
                d = row["delay_mins"]
                s = row["speed_kmh"]
                card_class = "smooth" if d <= 4 else ("moderate" if d <= 10 else "jammed")
                badge_class = card_class
                badge_text = ("SMOOTH" if d <= 4 else ("MODERATE" if d <= 10 else "HEAVY JAM"))
                bar_color = ("#2ED573" if d <= 4 else ("#FFA502" if d <= 10 else "#FF4757"))
                bar_pct = min(int(s / 50 * 100), 100)
                weather_str_lower = str(row['weather']).lower()
                w_icon = "🌧️" if "rain" in weather_str_lower or "storm" in weather_str_lower else ("☁️" if "cloud" in weather_str_lower or "overcast" in weather_str_lower else "☀️")
                with cols[index]:
                    st.markdown(f"""
                    <div class="road-card {card_class}">
                        <div class="road-name">{row['name']}</div>
                        <div class="road-speed">{s} <span>km/h</span></div>
                        <div class="speed-bar-bg"><div class="speed-bar-fill" style="width:{bar_pct}%;background:{bar_color};"></div></div>
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px;">
                            <span class="delay-badge {badge_class}">{badge_text} +{d}m</span>
                            <span class="weather-tag">{w_icon} {row['weather'].split(',')[1].strip() if ',' in str(row['weather']) else row['weather']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        if len(df_sorted) > 9:
            st.markdown(f'<div style="font-size:0.72rem;color:#5C6680;margin-top:8px;">+{len(df_sorted)-9} more nodes within nominal thresholds</div>', unsafe_allow_html=True)

else:
    st.markdown('<div style="text-align:center;padding:60px;color:#5C6680;"><div style="font-size:2rem;">📡</div><div style="font-size:1rem;margin-top:12px;">Awaiting telemetry uplink...</div></div>', unsafe_allow_html=True)
