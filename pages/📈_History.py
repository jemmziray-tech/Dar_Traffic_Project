import os
import json
import pandas as pd
import plotly.express as px
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# --- 1. Setup Page Config ---
st.set_page_config(page_title="Traffic Trends", layout="wide", page_icon="📈")

# --- 2. Connect to Firebase ---
if not firebase_admin._apps:
    try:
        if os.path.exists("firebase-key.json"):
            cred = credentials.Certificate("firebase-key.json")
        elif "firebase" in st.secrets:
            key_dict = json.loads(st.secrets["firebase"]["key_data"])
            cred = credentials.Certificate(key_dict)
        else:
            st.error("No valid Firebase credentials found.")
            st.stop()
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Failed to connect: {e}")
        st.stop()

db = firestore.client()


# --- 3. Functions ---
@st.cache_data(ttl=300)  # Caches the road list for 5 minutes
def get_roads_list():
    docs = db.collection("live_traffic").stream()
    return [doc.id for doc in docs]


@st.cache_data(ttl=300)  # Caches the heavy history payload for 5 minutes
def get_historical_data(road_id):
    stats_ref = db.collection("traffic_history")
    query = (
        stats_ref.where("road_id", "==", road_id)
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(200)
    )
    results = query.stream()
    return pd.DataFrame([doc.to_dict() for doc in results])


# --- 4. Main UI ---
st.title("📈 Historical Traffic Intelligence")
st.sidebar.header("Analysis Filters")

roads = get_roads_list()
selected_road = st.sidebar.selectbox("Choose a road to analyze", roads)

if selected_road:
    hist_df = get_historical_data(selected_road)
    if not hist_df.empty:
        # Convert timestamp to a Datetime object
        hist_df["timestamp"] = pd.to_datetime(hist_df["timestamp"])

        # TIMEZONE FIX: Convert from UTC to East Africa Time (Tanzania)
        hist_df["timestamp"] = hist_df["timestamp"].dt.tz_convert(
            "Africa/Dar_es_Salaam"
        )

        st.subheader(f"Delay History: {selected_road}")
        fig = px.area(
            hist_df,
            x="timestamp",
            y="delay_mins",
            title="Congestion Level (Minutes)",
            color_discrete_sequence=["#ff4b4b"],
            template="plotly_dark",
        )
        st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Speed vs Weather")
            
            # --- THE FIX: Extract just the condition (Clear, Rainy, Cloudy) for the colors ---
            hist_df['condition_only'] = hist_df['weather'].apply(lambda x: x.split(', ')[1] if ', ' in x else x)
            
            fig_speed = px.scatter(
                hist_df,
                x="timestamp",
                y="speed_kmh",
                color="condition_only",  # Use the clean categories for colors
                size="delay_mins",
                hover_name="weather",    # Keep the exact temp in the hover tooltip!
                color_discrete_map={
                    "Clear": "#00d2ff",   # Bright blue for clear
                    "Cloudy": "#9e9e9e",  # Grey for clouds
                    "Rainy": "#0047b3"    # Deep blue/purple for rain
                },
                template="plotly_dark",
            )
            st.plotly_chart(fig_speed, use_container_width=True)

        with col2:
            st.subheader("Traffic Status Distribution")
            fig_pie = px.pie(
                hist_df,
                names="status",
                color_discrete_map={
                    "Smooth": "#28a745",
                    "Moderate": "#ffc107",
                    "Heavy Jam": "#dc3545",
                },
            )
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Collecting data... check back after the next scheduled run!")
