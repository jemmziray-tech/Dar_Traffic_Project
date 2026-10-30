import os
import streamlit as st

def get_secret(name, default=None):
    value = os.getenv(name)
    if value:
        return value
    try:
        return st.secrets.get(name, default)
    except FileNotFoundError:
        return default


@st.cache_resource
def get_db():
    """Read only the fresh project's public traffic; never load old credentials."""
    from firestore_public import PublicTrafficReader
    return PublicTrafficReader()


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


def fresh_traffic_frame(frame, max_age_minutes=90):
    """Only expose recent, traffic-aware observations from the corrected collector."""
    import pandas as pd
    if frame.empty or not {"timestamp", "schema_version", "traffic_observed"}.issubset(frame.columns):
        return frame.iloc[:0].copy()
    observed = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    age = pd.Timestamp.now(tz="UTC") - observed
    return frame[(frame["schema_version"] == 2) & (frame["traffic_observed"] == True)
                 & age.between(pd.Timedelta(0), pd.Timedelta(minutes=max_age_minutes))].copy()
