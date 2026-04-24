import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import plotly.express as px

# --- 1. Setup Page Config ---
st.set_page_config(page_title="Traffic Trends", layout="wide", page_icon="📈")

# --- 2. Connect to Firebase (Stable Multi-Page Logic) ---
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-key.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()


# --- 3. Functions ---
def get_roads_list():
    docs = db.collection("live_traffic").stream()
    return [doc.id for doc in docs]


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
st.markdown("Analyze long-term patterns and weather correlations.")

# Sidebar for road selection
st.sidebar.header("Analysis Filters")
roads = get_roads_list()
selected_road = st.sidebar.selectbox("Choose a road to analyze", roads)

if selected_road:
    hist_df = get_historical_data(selected_road)

    if not hist_df.empty:
        hist_df["timestamp"] = pd.to_datetime(hist_df["timestamp"])

        # --- ROW 1: Trend Area Chart ---
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

        # --- ROW 2: Two Columns ---
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Speed vs Weather")
            fig_speed = px.scatter(
                hist_df,
                x="timestamp",
                y="speed_kmh",
                color="weather",
                size="delay_mins",
                title="Velocity Correlation",
                template="plotly_dark",
            )
            st.plotly_chart(fig_speed, use_container_width=True)

        with col2:
            st.subheader("Traffic Status Distribution")
            fig_pie = px.pie(
                hist_df,
                names="status",
                title="Frequency of Jams",
                color_discrete_map={
                    "Smooth": "#28a745",
                    "Moderate": "#ffc107",
                    "Heavy Jam": "#dc3545",
                },
            )
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info(
            f"Collecting data for {selected_road}... Check back after the next scheduled run!"
        )
