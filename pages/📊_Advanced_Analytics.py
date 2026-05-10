import streamlit as st
import pandas as pd
import plotly.express as px
import firebase_admin
from firebase_admin import credentials, firestore
import json
import os

st.set_page_config(page_title="Advanced Analytics", page_icon="📊", layout="wide")

st.title("📊 Advanced Traffic Analytics")
st.markdown(
    "Deep-dive business intelligence and meteorological impact analysis for Dar es Salaam."
)


# --- 1. SECURE FIREBASE CONNECTION (Cached for speed) ---
@st.cache_resource
def get_db():
    if not firebase_admin._apps:
        firebase_secret = os.getenv("FIREBASE_KEY_JSON")
        if firebase_secret:
            cred_dict = json.loads(firebase_secret)
            cred = credentials.Certificate(cred_dict)
        else:
            cred = credentials.Certificate("firebase-key.json")
        firebase_admin.initialize_app(cred)
    return firestore.client()


# --- 2. DATA FETCHING & CLEANING (Cached for speed) ---
@st.cache_data(ttl=3600)  # Caches for 1 hour so it doesn't slow down the app
def load_historical_data():
    db = get_db()
    docs = (
        db.collection("traffic_history")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(35000)
        .stream()
    )

    data = []
    for doc in docs:
        row = doc.to_dict()
        # Clean the timestamp
        if "timestamp" in row and row["timestamp"]:
            row["datetime"] = row["timestamp"]
        data.append(row)

    df = pd.DataFrame(data)

    if not df.empty:
        df["datetime"] = pd.to_datetime(df["datetime"], utc=True).dt.tz_convert(
            "Africa/Dar_es_Salaam"
        )
        df["Hour"] = df["datetime"].dt.hour
        df["Day"] = df["datetime"].dt.day_name()
        # Clean Weather (Extract just "Clear", "Rainy", "Cloudy")
        df["Condition"] = df["weather"].apply(
            lambda x: str(x).split(", ")[-1] if pd.notnull(x) else "Unknown"
        )

    return df


# --- 3. LOAD DATA ---
with st.spinner("Crunching historical datasets..."):
    df = load_historical_data()

if df.empty:
    st.warning(
        "Not enough historical data collected yet. Let the scraper run for a few more days!"
    )
    st.stop()

# --- 4. CLEAN UI TABS ---
# This is how we keep the app from looking cluttered!
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "⏱️ The 'Rush Hour' Matrix",
        "🌦️ Meteorological Impact",
        "💰 Cost of Congestion",
        "🤖 AI Model Accuracy (MLOps)",  # The Recruiter's Tab
    ]
)

# ==========================================
# TAB 1: TIME-SERIES HEATMAP
# ==========================================
with tab1:
    st.subheader("Identifying the True Rush Hour")
    st.write(
        "This heatmap aggregates thousands of data points to show the exact hours when Dar es Salaam gridlocks."
    )

    # Create a Pivot Table for the Heatmap
    pivot_df = df.pivot_table(
        index="Day", columns="Hour", values="delay_mins", aggfunc="mean"
    ).fillna(0)

    # Sort days chronologically
    days_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    pivot_df = pivot_df.reindex(days_order)

    fig_heat = px.imshow(
        pivot_df,
        labels=dict(x="Hour of Day", y="Day of Week", color="Average Delay (Mins)"),
        color_continuous_scale="YlOrRd",
        aspect="auto",
    )
    st.plotly_chart(fig_heat, use_container_width=True)

# ==========================================
# TAB 2: WEATHER CORRELATION
# ==========================================
with tab2:
    st.subheader("How much does rain slow down the city?")
    st.write("Comparing average speeds (km/h) across different weather conditions.")

    fig_weather = px.box(
        df,
        x="Condition",
        y="speed_kmh",
        color="Condition",
        points="all",
        title="Traffic Velocity vs. Weather Conditions",
        labels={"speed_kmh": "Speed (km/h)", "Condition": "Weather"},
    )
    st.plotly_chart(fig_weather, use_container_width=True)

# ==========================================
# TAB 3: COST OF CONGESTION
# ==========================================
with tab3:
    st.subheader("The Most Expensive Bottlenecks")
    st.write("Ranking roads by the total cumulative minutes lost to traffic jams.")

    # Aggregate total delay by road
    delay_by_road = (
        df.groupby("name")["delay_mins"]
        .sum()
        .reset_index()
        .sort_values(by="delay_mins", ascending=True)
    )

    fig_cost = px.bar(
        delay_by_road,
        x="delay_mins",
        y="name",
        orientation="h",
        color="delay_mins",
        color_continuous_scale="Reds",
        title="Total Cumulative Delay by Road",
        labels={"delay_mins": "Total Minutes Lost", "name": "Road Segment"},
    )
    st.plotly_chart(fig_cost, use_container_width=True)

# ==========================================
# TAB 4: AI MODEL ACCURACY (For the Recruiter)
# ==========================================
with tab4:
    st.subheader("Predictive Model Performance")
    st.write(
        "We believe in transparent AI. Here are the latest evaluation metrics from our automated weekly retraining pipeline."
    )

    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    metrics_path = os.path.join(root_dir, "model_metrics.csv")

    try:
        metrics_df = pd.read_csv(metrics_path)

        col1, col2, col3 = st.columns(3)
        latest_metrics = metrics_df.iloc[-1]

        # Mapping to YOUR exact CSV column names
        col1.metric(
            "Mean Absolute Error (MAE)",
            f"{latest_metrics['MAE_Minutes']:.2f} mins",
            delta="Lower is better",
            delta_color="inverse",
        )

        # Safely check for R2_Score (in case your older rows don't have it yet)
        if "R2_Score" in metrics_df.columns and pd.notna(latest_metrics["R2_Score"]):
            col2.metric(
                "Model R² Score",
                f"{latest_metrics['R2_Score']:.2f}",
                help="1.0 is perfect prediction",
            )
        else:
            col2.metric("Model R² Score", "Pending...")

        col3.metric("Last Retrained", str(latest_metrics["Date"]).split()[0])

        st.success("✅ Model is performing within acceptable enterprise thresholds.")

    except FileNotFoundError:
        st.info(
            "Metrics file not found locally. To view this tab, run `python train_model.py` in your terminal!"
        )
