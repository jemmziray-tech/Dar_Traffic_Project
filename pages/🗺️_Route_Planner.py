import os
import json
from datetime import datetime
import pytz
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# ─────────────────────────────────────────────────────────────────────────────
# 1. PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Route Planner — Dar Traffic",
    layout="wide",
    page_icon="🗺️",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# 2. PREMIUM CSS DESIGN SYSTEM
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, [class*="css"], .stApp { font-family: 'Inter', sans-serif !important; background-color: #0A0F1E; color: #E8EAF0; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0D1426 0%, #0A0F1E 100%) !important; border-right: 1px solid rgba(0,212,255,0.1); }
.block-container { padding-top: 1.8rem; padding-bottom: 2rem; max-width: 98%; }
div[data-testid="stMetricValue"] { font-weight: 700; font-size: 1.4rem !important; letter-spacing: -0.5px; color: #FFFFFF; }
div[data-testid="stMetricLabel"] { color: #8892A4 !important; font-size: 0.72rem; font-weight: 500; letter-spacing: 0.5px; text-transform: uppercase; }

.page-header { font-size: 1.8rem; font-weight: 800; color: #FFFFFF; letter-spacing: -0.8px; }
.page-sub { font-size: 0.85rem; color: #5C6680; margin-top: 4px; }

/* Route cards */
.route-card {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 20px 24px;
    margin-bottom: 14px;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s, box-shadow 0.2s;
}
.route-card:hover { border-color: rgba(0,212,255,0.3); box-shadow: 0 0 24px rgba(0,212,255,0.06); }
.route-card.recommended {
    border-color: rgba(0,212,255,0.35);
    background: rgba(0,212,255,0.03);
}
.route-card.recommended::after {
    content: '🏆 RECOMMENDED';
    position: absolute; top: 14px; right: 16px;
    font-size: 0.65rem; font-weight: 700; letter-spacing: 1px;
    color: #00D4FF; background: rgba(0,212,255,0.1);
    border: 1px solid rgba(0,212,255,0.25);
    padding: 3px 9px; border-radius: 20px;
}
.route-title { font-size: 1rem; font-weight: 700; color: #FFFFFF; margin-bottom: 12px; }
.route-total { font-size: 2.2rem; font-weight: 800; color: #FFFFFF; line-height: 1; }
.route-total span { font-size: 0.9rem; font-weight: 400; color: #8892A4; }
.route-extra { font-size: 0.78rem; color: #5C6680; margin-top: 4px; }

/* Segment items */
.seg-item {
    display: flex; align-items: center; gap: 10px;
    padding: 9px 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    font-size: 0.82rem;
}
.seg-item:last-child { border-bottom: none; }
.seg-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.seg-name { flex: 1; color: #C8D0E0; font-weight: 500; }
.seg-time { color: #FFFFFF; font-weight: 600; white-space: nowrap; }
.seg-badge { font-size: 0.68rem; font-weight: 600; padding: 2px 7px; border-radius: 10px; white-space: nowrap; }
.seg-smooth { background: rgba(46,213,115,0.1); color: #2ED573; border: 1px solid rgba(46,213,115,0.25); }
.seg-moderate { background: rgba(255,165,2,0.1); color: #FFA502; border: 1px solid rgba(255,165,2,0.25); }
.seg-jammed { background: rgba(255,71,87,0.1); color: #FF4757; border: 1px solid rgba(255,71,87,0.25); }

/* Departure tip card */
.tip-card {
    background: rgba(46,213,115,0.05);
    border: 1px solid rgba(46,213,115,0.2);
    border-radius: 12px;
    padding: 16px 20px;
    margin-top: 16px;
}
.tip-title { font-size: 0.72rem; font-weight: 700; color: #2ED573; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px; }

/* Input select styling */
.stButton > button { border-radius: 8px !important; font-weight: 600 !important; }
.stButton > button[kind="primary"] { background: linear-gradient(135deg, #00D4FF, #0099CC) !important; border: none !important; color: #0A0F1E !important; }

/* Divider */
.fancy-divider { height: 1px; background: linear-gradient(90deg, rgba(0,212,255,0.3), transparent); margin: 20px 0; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 3. FIREBASE CONNECTION
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_db():
    if not firebase_admin._apps:
        firebase_secret = os.getenv("FIREBASE_KEY_JSON")
        if firebase_secret:
            cred = credentials.Certificate(json.loads(firebase_secret))
        elif os.path.exists("firebase-key.json"):
            cred = credentials.Certificate("firebase-key.json")
        elif "firebase" in st.secrets:
            key_dict = (
                json.loads(st.secrets["firebase"]["key_data"])
                if "key_data" in st.secrets["firebase"]
                else dict(st.secrets["firebase"])
            )
            cred = credentials.Certificate(key_dict)
        else:
            st.error("Authentication failure: No Firebase credentials found.")
            st.stop()
        firebase_admin.initialize_app(cred)
    return firestore.client()

# ─────────────────────────────────────────────────────────────────────────────
# 4. DAR ES SALAAM ROAD NETWORK GRAPH
# Each entry: (road_id_in_firebase, display_name, base_travel_mins)
# ─────────────────────────────────────────────────────────────────────────────
# Canonical road IDs — must EXACTLY match document IDs in Firestore live_traffic collection
# (these come from the 'id' field in scrape_traffic.py ROADS list)
ROAD_IDS = {
    "ubungo":               "Morogoro Rd (Ubungo)",
    "posta_to_kimara":      "Mega-Route: Posta–Kimara (Morogoro Rd)",
    "mwenge":               "Bagamoyo Rd (Mwenge)",
    "old_bagamoyo":         "Old Bagamoyo Rd (Victoria)",
    "posta_to_tegeta":      "Mega-Route: Posta–Tegeta (Bagamoyo Rd)",
    "kilwa_mbagala":        "Kilwa Rd (Mbagala)",
    "tazara":               "Nyerere Rd (TAZARA)",
    "mandela_buguruni":     "Mandela Rd (Port Link)",
    "morocco_intersection": "Kawawa Rd (Morocco–Kinondoni)",
    "sam_nujoma":           "Sam Nujoma Rd",
    "goba_massana":         "Goba Road (Massana–Goba Center)",
    "posta_to_gongolamboto":"Mega-Route: Posta–Gongo la Mboto",
    "changombe_road":       "Chang'ombe Road (Temeke)",
    "kigogo_roundabout":    "Kawawa Rd (Kigogo Choke)",
    "tabata_dampo":         "Tabata Road (Mandela–Segerea)",
    "selander":             "Ali Hassan Mwinyi Rd",
    "sinza_mori":           "Sinza Road",
    "mwai_kibaki":          "Mwai Kibaki Rd (Kawe–Mikocheni)",
    "fire_upanga":          "UN Road (Fire–Upanga)",
    "kamata_gerezani":      "Kamata / Gerezani (Port Entry)",
    "uhuru_street":         "Uhuru Street (Ilala–Town)",
}

# ROUTE NETWORK — each route lists real Firestore document IDs in traverse order
ROUTES = {
    ("Kimara", "Posta / CBD"): {
        "Route 1 — Morogoro Rd Direct": ["posta_to_kimara", "ubungo"],
        "Route 2 — Via Sam Nujoma": ["sam_nujoma", "morocco_intersection", "tazara"],
    },
    ("Tegeta", "Posta / CBD"): {
        "Route 1 — Bagamoyo Rd Direct": ["posta_to_tegeta", "mwenge"],
        "Route 2 — Via Mwenge + Sam Nujoma": ["old_bagamoyo", "mwenge", "sam_nujoma"],
    },
    ("Mbagala", "Posta / CBD"): {
        "Route 1 — Kilwa Rd": ["kilwa_mbagala", "changombe_road"],
        "Route 2 — Mandela + Nyerere": ["mandela_buguruni", "tazara"],
    },
    ("Goba", "Posta / CBD"): {
        "Route 1 — Goba Rd + Kawawa": ["goba_massana", "morocco_intersection", "sam_nujoma"],
        "Route 2 — Via Mwenge": ["goba_massana", "mwenge"],
    },
    ("Morocco / Kinondoni", "Posta / CBD"): {
        "Route 1 — Kawawa Rd Direct": ["morocco_intersection", "sam_nujoma"],
        "Route 2 — Via Bagamoyo Rd": ["mwenge", "selander"],
    },
    ("Port / Bandarini", "Posta / CBD"): {
        "Route 1 — Mandela Rd": ["mandela_buguruni", "kamata_gerezani"],
        "Route 2 — Via Nyerere Rd": ["tazara", "uhuru_street"],
    },
    ("TAZARA / Kigamboni", "Posta / CBD"): {
        "Route 1 — Nyerere Rd Direct": ["tazara", "changombe_road"],
        "Route 2 — Via Mandela": ["mandela_buguruni", "tazara"],
    },
    ("Gongo la Mboto", "Posta / CBD"): {
        "Route 1 — Direct Corridor": ["posta_to_gongolamboto", "tazara"],
        "Route 2 — Via Tabata": ["tabata_dampo", "tazara"],
    },
    ("Sinza / Kinondoni", "Posta / CBD"): {
        "Route 1 — Sinza + Sam Nujoma": ["sinza_mori", "sam_nujoma"],
        "Route 2 — Via Kawawa": ["sinza_mori", "kigogo_roundabout", "uhuru_street"],
    },
    ("Kawe / Mikocheni", "Posta / CBD"): {
        "Route 1 — Mwai Kibaki + Old Bagamoyo": ["mwai_kibaki", "old_bagamoyo", "selander"],
        "Route 2 — Via Mwenge": ["mwai_kibaki", "mwenge", "sam_nujoma"],
    },
    
    # === NEW: CROSS-CITY ROUTES ===
    ("Ubungo", "Mwenge / Makumbusho"): {
        "Route 1 — Sam Nujoma Direct": ["sam_nujoma"],
        "Route 2 — Via Sinza": ["sinza_mori", "mwenge"],
    },
    ("Tegeta", "Ubungo"): {
        "Route 1 — Bagamoyo Rd + Sam Nujoma": ["posta_to_tegeta", "mwenge", "sam_nujoma"],
        "Route 2 — Via Goba": ["goba_massana", "sam_nujoma"],
    },
    ("Posta / CBD", "Airport (JNIA)"): {
        "Route 1 — Nyerere Rd Direct": ["tazara", "posta_to_gongolamboto"],
        "Route 2 — Via Uhuru St & Mandela": ["uhuru_street", "mandela_buguruni", "tazara"],
    },
    ("Mwenge / Makumbusho", "Airport (JNIA)"): {
        "Route 1 — Sam Nujoma + Mandela": ["sam_nujoma", "mandela_buguruni", "tazara"],
        "Route 2 — Via Kawawa & Nyerere": ["morocco_intersection", "kigogo_roundabout", "tazara"],
    },
    ("Tabata", "Posta / CBD"): {
        "Route 1 — Uhuru St": ["tabata_dampo", "uhuru_street"],
        "Route 2 — Via Mandela & Nyerere": ["tabata_dampo", "mandela_buguruni", "tazara"],
    },
    ("Tabata", "Mwenge / Makumbusho"): {
        "Route 1 — Mandela + Sam Nujoma": ["tabata_dampo", "mandela_buguruni", "sam_nujoma"],
        "Route 2 — Via Kigogo & Kawawa": ["tabata_dampo", "kigogo_roundabout", "morocco_intersection"],
    }
}

ORIGINS = sorted(list(set(o for o, _ in ROUTES.keys())))

# ─────────────────────────────────────────────────────────────────────────────
# 5. FETCH LIVE DELAYS FROM FIREBASE
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def get_live_delays():
    db = get_db()
    docs = db.collection("live_traffic").stream()
    delays = {}
    speeds = {}
    weathers = {}
    for doc in docs:
        d = doc.to_dict()
        road_id = d.get("road_id", doc.id)
        delays[road_id] = d.get("delay_mins", 0)
        speeds[road_id] = d.get("speed_kmh", 30)
        weathers[road_id] = d.get("weather", "Clear")
    return delays, speeds, weathers

# ─────────────────────────────────────────────────────────────────────────────
# 6. HELPER: Color for delay
# ─────────────────────────────────────────────────────────────────────────────
def delay_style(d):
    if d <= 4:
        return "seg-smooth", "#2ED573", "SMOOTH"
    elif d <= 10:
        return "seg-moderate", "#FFA502", "MODERATE"
    else:
        return "seg-jammed", "#FF4757", "HEAVY JAM"

def dot_color(d):
    return "#2ED573" if d <= 4 else ("#FFA502" if d <= 10 else "#FF4757")

# ─────────────────────────────────────────────────────────────────────────────
# 7. PAGE HEADER
# ─────────────────────────────────────────────────────────────────────────────
tz = pytz.timezone("Africa/Dar_es_Salaam")
now = datetime.now(tz)

st.markdown("""
<div class="page-header">🗺️ Route A → B Planner</div>
<div class="page-sub">Live journey stitching across Dar es Salaam corridors — find the fastest path right now</div>
""", unsafe_allow_html=True)
st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 8. ROUTE SELECTOR
# ─────────────────────────────────────────────────────────────────────────────
sel_col, _, dest_col = st.columns([2, 0.2, 2])
with sel_col:
    st.markdown('<div style="font-size:0.7rem;color:#8892A4;text-transform:uppercase;letter-spacing:1px;font-weight:600;margin-bottom:6px;">🟢 Starting From</div>', unsafe_allow_html=True)
    origin = st.selectbox("Origin", ORIGINS, label_visibility="collapsed", key="origin_sel")

with dest_col:
    valid_destinations = sorted(list(set(d for o, d in ROUTES.keys() if o == origin)))
    st.markdown('<div style="font-size:0.7rem;color:#8892A4;text-transform:uppercase;letter-spacing:1px;font-weight:600;margin-bottom:6px;">🏁 Going To</div>', unsafe_allow_html=True)
    destination = st.selectbox("Destination", valid_destinations, label_visibility="collapsed", key="dest_sel")

st.write("")
plan_btn = st.button("⚡ Plan My Route", type="primary", use_container_width=False)
st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 9. ROUTE COMPUTATION
# ─────────────────────────────────────────────────────────────────────────────
route_key = (origin, destination)

if route_key not in ROUTES:
    st.markdown(f"""
    <div style="background:rgba(255,165,2,0.06);border:1px solid rgba(255,165,2,0.2);border-radius:12px;padding:20px;text-align:center;">
        <div style="font-size:1.4rem;">🚧</div>
        <div style="font-weight:600;color:#FFA502;margin-top:8px;">Route not yet mapped</div>
        <div style="font-size:0.8rem;color:#5C6680;margin-top:4px;">Coverage expanding — try another origin point</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Auto-compute on load, also on button click
with st.spinner("Fetching live corridor telemetry..."):
    live_delays, live_speeds, live_weathers = get_live_delays()

route_options = ROUTES[route_key]
computed_routes = {}

for route_name, road_ids in route_options.items():
    segments = []
    total_mins = 0
    total_delay = 0
    base_mins = 0
    for rid in road_ids:
        delay = live_delays.get(rid, 0)
        speed = live_speeds.get(rid, 30)
        weather = live_weathers.get(rid, "Clear")
        display_name = ROAD_IDS.get(rid, rid.replace("_", " ").title())
        # Estimate base travel: 30 km/h free-flow assumption per segment
        seg_free_mins = max(8, round(30 / max(speed, 1) * 10))
        seg_total = seg_free_mins + delay
        segments.append({
            "name": display_name,
            "delay": delay,
            "speed": speed,
            "weather": weather,
            "seg_mins": seg_total,
            "free_mins": seg_free_mins,
        })
        total_mins += seg_total
        total_delay += delay
        base_mins += seg_free_mins
    computed_routes[route_name] = {
        "segments": segments,
        "total_mins": total_mins,
        "total_delay": total_delay,
        "base_mins": base_mins,
    }

# Sort by total time — best route first
sorted_routes = sorted(computed_routes.items(), key=lambda x: x[1]["total_mins"])
best_route_name = sorted_routes[0][0]

# ─────────────────────────────────────────────────────────────────────────────
# 10. RESULTS LAYOUT
# ─────────────────────────────────────────────────────────────────────────────
left_col, right_col = st.columns([3, 2], gap="large")

with left_col:
    st.markdown(f'<div style="font-size:0.72rem;font-weight:700;color:#00D4FF;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:14px;">◈ {origin} → {destination}</div>', unsafe_allow_html=True)

    for route_name, data in sorted_routes:
        is_best = (route_name == best_route_name)
        card_class = "route-card recommended" if is_best else "route-card"
        extra_delay = data["total_delay"]
        delay_txt = f"+{extra_delay} min extra vs free-flow" if extra_delay > 0 else "No extra delay"

        # Build segment HTML
        segs_html = ""
        for seg in data["segments"]:
            cls, clr, lbl = delay_style(seg["delay"])
            w_icon = "🌧️" if "Rain" in seg["weather"] else ("☁️" if "Cloud" in seg["weather"] else "☀️")
            segs_html += f"""
            <div class="seg-item">
                <div class="seg-dot" style="background:{clr};box-shadow:0 0 6px {clr}88;"></div>
                <div class="seg-name">{seg['name']}</div>
                <span class="seg-badge {cls}">{lbl}</span>
                <div class="seg-time">{seg['seg_mins']} min</div>
            </div>"""

        st.markdown(f"""
        <div class="{card_class}">
            <div class="route-title">{route_name}</div>
            <div class="route-total">{data['total_mins']} <span>mins total</span></div>
            <div class="route-extra">{delay_txt}</div>
            <div style="margin-top:14px;">{segs_html}</div>
        </div>
        """, unsafe_allow_html=True)

with right_col:
    # Live network summary metrics
    st.markdown('<div style="font-size:0.72rem;font-weight:700;color:#00D4FF;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:14px;">◈ Live Network at a Glance</div>', unsafe_allow_html=True)

    best = sorted_routes[0][1]
    worst = sorted_routes[-1][1]

    m1, m2 = st.columns(2)
    m1.metric("Fastest Route", f"{best['total_mins']} mins", f"Save {worst['total_mins'] - best['total_mins']} mins vs alt.")
    m2.metric("Extra Delay", f"+{best['total_delay']} mins", f"vs {best['base_mins']} min free-flow", delta_color="inverse")

    st.write("")

    # Departure recommendation
    hour = now.hour
    if 6 <= hour <= 8:
        dep_tip = "🕐 You're in peak morning rush. Consider departing **after 09:00 EAT** when Morogoro & Bagamoyo Rds ease significantly."
        tip_color = "#FF4757"
    elif 16 <= hour <= 19:
        dep_tip = "🕔 Evening rush is active. If possible, depart **after 20:00 EAT** to avoid inbound city corridor jams."
        tip_color = "#FFA502"
    elif 12 <= hour <= 13:
        dep_tip = "🌤️ Midday — conditions are moderate. **Now is a good time to travel.** Delays are near daily minimum."
        tip_color = "#2ED573"
    else:
        dep_tip = "✅ Off-peak window. **Conditions are optimal right now.** Depart when ready."
        tip_color = "#2ED573"

    st.markdown(f"""
    <div class="tip-card" style="border-color:rgba(var(--tip-r),var(--tip-g),var(--tip-b),0.25);">
        <div class="tip-title">⏱ Departure Intelligence</div>
        <div style="font-size:0.85rem;color:#C8D0E0;line-height:1.6;">{dep_tip}</div>
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    # Corridor status for all segments in best route
    st.markdown('<div style="font-size:0.72rem;font-weight:700;color:#00D4FF;letter-spacing:1.5px;text-transform:uppercase;margin-top:8px;margin-bottom:12px;">◈ Recommended Route Breakdown</div>', unsafe_allow_html=True)

    for seg in best["segments"]:
        cls, clr, lbl = delay_style(seg["delay"])
        bar_pct = min(int(seg["speed"] / 50 * 100), 100)
        w_icon = "🌧️" if "Rain" in seg["weather"] else ("☁️" if "Cloud" in seg["weather"] else "☀️")
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:12px 14px;margin-bottom:8px;">
            <div style="font-size:0.72rem;font-weight:600;color:#8892A4;text-transform:uppercase;letter-spacing:0.5px;">{seg['name']}</div>
            <div style="font-size:1.2rem;font-weight:800;color:#FFFFFF;margin:4px 0;">{seg['speed']} <span style='font-size:0.7rem;color:#8892A4;font-weight:400;'>km/h</span></div>
            <div style="background:rgba(255,255,255,0.06);border-radius:4px;height:3px;margin:6px 0;overflow:hidden;">
                <div style="width:{bar_pct}%;height:3px;background:{clr};border-radius:4px;"></div>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-size:0.68rem;font-weight:600;padding:2px 7px;border-radius:10px;background:rgba(255,255,255,0.05);color:{clr};">{lbl} +{seg['delay']}m</span>
                <span style="font-size:0.68rem;color:#5C6680;">{w_icon} {seg['weather'].split(',')[1].strip() if ',' in str(seg['weather']) else seg['weather']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 11. SIDEBAR — QUICK STATS
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="padding:16px 0 8px 0;">
        <div style="font-size:0.65rem;color:#5C6680;text-transform:uppercase;letter-spacing:1px;font-weight:600;">🗺️ Route Planner</div>
        <div style="font-size:0.9rem;font-weight:700;color:#FFFFFF;margin-top:4px;">{origin}</div>
        <div style="font-size:0.72rem;color:#5C6680;">↓ to {destination}</div>
        <div style="font-size:0.72rem;color:#8892A4;margin-top:8px;">{now.strftime('%H:%M EAT · %d %b %Y')}</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown(f'<div style="font-size:0.65rem;color:#5C6680;text-transform:uppercase;letter-spacing:1px;font-weight:600;margin-bottom:8px;">Best Route</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:1.4rem;font-weight:800;color:#00D4FF;">{sorted_routes[0][1]["total_mins"]} mins</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:0.72rem;color:#5C6680;">{best_route_name}</div>', unsafe_allow_html=True)

    st.divider()
    st.markdown('<div style="font-size:0.65rem;color:#5C6680;text-transform:uppercase;letter-spacing:1px;font-weight:600;margin-bottom:10px;">All Routes</div>', unsafe_allow_html=True)
    for rname, rdata in sorted_routes:
        is_b = rname == best_route_name
        c = "#00D4FF" if is_b else "#8892A4"
        st.markdown(f'<div style="font-size:0.78rem;color:{c};font-weight:{"700" if is_b else "400"};margin-bottom:4px;">{"✓ " if is_b else ""}{rdata["total_mins"]}m — {rname.split("—")[0].strip()}</div>', unsafe_allow_html=True)

    if st.button("🔄 Refresh Data", use_container_width=True):
        get_live_delays.clear()
        st.rerun()
