import os
import json
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

@st.cache_resource
def get_db():
    """Initializes and returns a singleton Firestore client."""
    if not firebase_admin._apps:
        try:
            firebase_secret = os.getenv("FIREBASE_KEY_JSON")
            if firebase_secret:
                # GitHub Actions / local environment variable
                cred = credentials.Certificate(json.loads(firebase_secret))
            elif "firebase" in st.secrets:
                # Streamlit Cloud — reads from st.secrets
                key_dict = json.loads(st.secrets["firebase"]["key_data"]) if "key_data" in st.secrets["firebase"] else dict(st.secrets["firebase"])
                cred = credentials.Certificate(key_dict)
            elif os.path.exists("firebase-key.json"):
                # Local development fallback
                cred = credentials.Certificate("firebase-key.json")
            else:
                st.error("Authentication failure: No Firebase credentials found.", icon="🔒")
                st.stop()
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Failed to connect to Firebase: {e}", icon="⚠️")
            st.stop()
    return firestore.client()

def format_road_name(road_id):
    """Formats a road_id string into a Title Case human-readable name."""
    ROAD_MAP = {
        "ubungo": "Morogoro Rd (Ubungo)",
        "mwenge": "Bagamoyo Rd (Mwenge)",
        "selander": "Ali Hassan Mwinyi",
        "tazara": "Nyerere Rd (Tazara)",
        "mandela_buguruni": "Mandela Rd (Port Link)",
        "kilwa_mbagala": "Kilwa Rd (Mbagala)",
        "old_bagamoyo": "Old Bagamoyo Rd (Victoria)",
        "sam_nujoma": "Sam Nujoma Rd (Mwenge-Ubungo)",
        "uhuru_street": "Uhuru Street (Ilala)",
        "posta_to_tegeta": "Mega-Route: Posta to Tegeta",
        "posta_to_kimara": "Mega-Route: Posta to Kimara",
        "posta_to_gongolamboto": "Mega-Route: Posta to Airport",
        "tabata_dampo": "Tabata Road (Mandela to Segerea)",
        "kamata_gerezani": "Kamata (Port Entry)",
        "changombe_road": "Chang'ombe Road (Temeke)",
        "morocco_intersection": "Kawawa Rd (Morocco to Kinondoni)",
        "kigogo_roundabout": "Kawawa Rd (Kigogo Choke)",
        "fire_upanga": "UN Road (Fire to Upanga)",
        "mwai_kibaki": "Mwai Kibaki Rd (Kawe)",
        "sinza_mori": "Sinza Road (Mori to Bamaga)",
        "goba_massana": "Goba Road (Massana)",
    }
    return ROAD_MAP.get(road_id, str(road_id).replace("_", " ").title())

def map_weather(w):
    """Categorizes weather into Clear, Cloudy, or Rainy."""
    w = str(w).lower()
    if any(rain_word in w for rain_word in ["rain", "drizzle", "shower", "storm", "thunder"]):
        return "Rainy"
    elif any(cloud_word in w for cloud_word in ["cloud", "overcast"]):
        return "Cloudy"
    else:
        return "Clear"
