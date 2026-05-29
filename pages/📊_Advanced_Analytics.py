import os
import json
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from sklearn.cluster import KMeans
import joblib

# --- 1. SETUP PAGE CONFIG ---
st.set_page_config(
    page_title="Advanced Analytics", page_icon=":material/analytics:", layout="wide"
)

st.title(":material/query_stats: Enterprise Traffic Intelligence")
st.markdown(
    "Deep-dive business intelligence, unsupervised spatial clustering, and ML validation analysis."
)

# --- 2. SECURE FIREBASE CONNECTION ---
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

# --- 3. DATA FETCHING & V3 TRANSLATION LAYER ---
@st.cache_data(ttl=600) # Cache for 10 minutes
def load_historical_data():
    db = get_db()
    docs = db.collection("traffic_history").stream()
    df = pd.DataFrame([doc.to_dict() for doc in docs])

    if df.empty:
        return df

    # ==========================================
    # V3 FEATURE ENGINEERING TRANSLATION LAYER
    # ==========================================
    
    # 1. Temporal Engineering
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    if df["timestamp"].dt.tz is None:
        df["timestamp"] = df["timestamp"].dt.tz_localize("UTC").dt.tz_convert("Africa/Dar_es_Salaam")
    else:
        df["timestamp"] = df["timestamp"].dt.tz_convert("Africa/Dar_es_Salaam")

    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["is_weekend"] = df["day_of_week"].apply(lambda x: 1 if x >= 5 else 0)
    df["is_rush_hour"] = df["hour"].apply(lambda x: 1 if x in [7, 8, 16, 17, 18, 19] else 0)

    # 2. Weather Engineering
    df["temp_c"] = df["weather"].astype(str).str.extract(r'([0-9.]+)').astype(float)
    df["temp_c"] = df["temp_c"].fillna(25.0) 
    df["condition"] = df["weather"].apply(lambda x: str(x).split(", ")[1] if ", " in str(x) else "Clear")
    df["is_raining"] = df["condition"].apply(lambda x: 1 if "Rain" in str(x) else 0)

    # 3. Traffic Velocity Engineering (The Delta)
    df = df.sort_values(by=["road_id", "timestamp"])
    df["previous_delay"] = df.groupby("road_id")["delay_mins"].shift(1)
    df["delay_velocity"] = df["delay_mins"] - df["previous_delay"]
    df["delay_velocity"] = df["delay_velocity"].fillna(0) 

    return df

df = load_historical_data()

if df.empty:
    st.error("No telemetry data found in the database. Please check your scraper.")
    st.stop()

# --- 4. DASHBOARD VISUALIZATIONS ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Traffic Velocity (Momentum) by Hour")
    # Using the new velocity feature to show if traffic is getting better or worse
    fig_vel = px.line(
        df.groupby("hour")["delay_velocity"].mean().reset_index(),
        x="hour", y="delay_velocity", markers=True,
        title="Average Change in Delay (Mins) per Hour",
        labels={"delay_velocity": "Velocity (Mins)", "hour": "Time of Day"}
    )
    st.plotly_chart(fig_vel, use_container_width=True)

with col2:
    st.subheader("Gridlock Hotspots (Unsupervised Clustering)")
    # Using KMeans to find hidden patterns in numbers
    cluster_data = df[["hour", "delay_mins", "temp_c"]].dropna()
    if not cluster_data.empty:
        kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
        df.loc[cluster_data.index, "Cluster"] = kmeans.fit_predict(cluster_data).astype(str)
        fig_cluster = px.scatter(
            df, x="hour", y="delay_mins", color="Cluster",
            title="K-Means Pattern Recognition",
            labels={"hour": "Hour of Day", "delay_mins": "Delay (Mins)"}
        )
        st.plotly_chart(fig_cluster, use_container_width=True)

# --- 5. ML VALIDATION ENGINE ---
st.divider()
st.subheader("🔬 AI Validation Engine")
st.markdown("Auditing the V3 XGBoost model against live historical data.")

model_path = "traffic_model.pkl"
if os.path.exists(model_path):
    try:
        model = joblib.load(model_path)
        
        target_road = st.selectbox("Select Artery for Validation Audit:", df["road_id"].unique())
        df_val = df[df["road_id"] == target_road].copy()
        
        if not df_val.empty:
            # Feed the exact features the V3 model expects
            features = ["road_id", "hour", "day_of_week", "is_weekend", "is_rush_hour", "temp_c", "is_raining", "delay_velocity"]
            df_val["Predicted_Delay"] = model.predict(df_val[features])
            
            # Ensure predictions don't drop below 0 graphically
            df_val["Predicted_Delay"] = df_val["Predicted_Delay"].clip(lower=0)

            fig_val = go.Figure()
            fig_val.add_trace(go.Scatter(x=df_val["timestamp"], y=df_val["delay_mins"], mode="lines", name="Actual Delay (Reality)", line=dict(color="#FF4B4B")))
            fig_val.add_trace(go.Scatter(x=df_val["timestamp"], y=df_val["Predicted_Delay"], mode="lines", name="AI Prediction", line=dict(color="#4B8BBE", dash="dash")))
            
            fig_val.update_layout(template="plotly_dark", height=350, hovermode="x unified")
            st.plotly_chart(fig_val, use_container_width=True)
            
            error_margin = abs(df_val["delay_mins"] - df_val["Predicted_Delay"]).mean()
            st.info(f"**Insight:** The V3 Engine predicts traffic for **{target_road}** with an average variance of **±{error_margin:.1f} minutes** from physical reality.")
        
    except Exception as e:
        st.error(f"Validation Engine Offline: {e}")
else:
    st.warning("⚠️ V3 traffic_model.pkl not found. Train the model first.")
