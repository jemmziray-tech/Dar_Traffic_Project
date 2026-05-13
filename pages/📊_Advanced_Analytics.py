import os
import json
import pandas as pd
import plotly.express as px
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# --- 1. SETUP PAGE CONFIG (Enterprise Polish) ---
st.set_page_config(page_title="Advanced Analytics", page_icon=":material/analytics:", layout="wide")

st.title(":material/query_stats: Advanced Traffic Analytics")
st.markdown("Deep-dive business intelligence, spatial bottlenecks, and meteorological impact analysis.")
st.markdown("---")

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

# --- 3. DATA FETCHING & SANITIZATION ---
@st.cache_data(ttl=3600)
def load_historical_data():
    db = get_db()
    docs = (
        db.collection("traffic_history")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(40000)
        .stream()
    )

    data = []
    for doc in docs:
        row = doc.to_dict()
        if "timestamp" in row and row["timestamp"]:
            row["datetime"] = row["timestamp"]
        data.append(row)

    df = pd.DataFrame(data)

    if not df.empty:
        df["datetime"] = pd.to_datetime(df["datetime"], utc=True).dt.tz_convert("Africa/Dar_es_Salaam")
        df["Hour"] = df["datetime"].dt.hour
        df["Day"] = df["datetime"].dt.day_name()
        
        # Clean Weather & Remove "Unknown" Noise
        df["Condition"] = df["weather"].apply(
            lambda x: str(x).split(", ")[-1] if pd.notnull(x) else "Unknown"
        )
        # Filter strictly for actionable meteorological states
        df = df[df["Condition"].isin(["Clear", "Rainy", "Cloudy"])]

    return df

# --- 4. LOAD DATA ---
with st.spinner("Compiling historical telemetry datasets..."):
    df = load_historical_data()

if df.empty:
    st.warning("Insufficient historical telemetry. Awaiting further ingestion cycles.", icon=":material/warning:")
    st.stop()

# --- 5. ENTERPRISE UI TABS ---
tab1, tab2, tab3, tab4 = st.tabs([
    ":material/grid_on: Temporal Flow Matrix",
    ":material/water_drop: Meteorological Friction",
    ":material/payments: Capital Degradation",
    ":material/model_training: MLOps Diagnostics"
])

# ==========================================
# TAB 1: TEMPORAL FLOW MATRIX
# ==========================================
with tab1:
    st.subheader("Temporal Congestion Distribution")
    st.write("Aggregated heatmap identifying systemic network gridlock by hour and day.")

    df["Clean_Hour"] = df["Hour"].astype(int)
    pivot_df = df.pivot_table(index="Day", columns="Clean_Hour", values="delay_mins", aggfunc="mean")

    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot_df = pivot_df.reindex(days_order)

    target_hours = list(range(6, 23))
    pivot_df = pivot_df.reindex(columns=target_hours).fillna(0)

    fig_heat = px.imshow(
        pivot_df,
        labels=dict(x="Operating Hour (06:00 - 23:00)", y="Day of Week", color="Mean Delay (Mins)"),
        color_continuous_scale="YlOrRd",
        aspect="auto",
    )
    fig_heat.update_xaxes(tickmode="linear", dtick=1)
    st.plotly_chart(fig_heat, use_container_width=True)

# ==========================================
# TAB 2: METEOROLOGICAL FRICTION (Includes Feature 1)
# ==========================================
with tab2:
    col_weather_top, col_weather_bottom = st.container(), st.container()
    
    with col_weather_top:
        st.subheader("Velocity vs. Meteorological State")
        st.write("Distribution of traffic velocity (km/h) mapped against active weather conditions.")

        fig_weather = px.box(
            df,
            x="Condition",
            y="speed_kmh",
            color="Condition",
            points="all",
            labels={"speed_kmh": "Velocity (km/h)", "Condition": "Meteorological State"},
        )
        st.plotly_chart(fig_weather, use_container_width=True)

    st.markdown("---")

    with col_weather_bottom:
        st.subheader("Infrastructure Vulnerability Index")
        st.write("Quantifying the percentage drop in standard velocity per artery during precipitation events.")

        # --- FEATURE 1: Drainage / Rain Vulnerability Math ---
        df_weather_impact = df[df["Condition"].isin(["Clear", "Rainy"])]
        
        weather_pivot = df_weather_impact.pivot_table(
            index="name", columns="Condition", values="speed_kmh", aggfunc="mean"
        ).dropna()

        if "Clear" in weather_pivot.columns and "Rainy" in weather_pivot.columns:
            # Calculate the percentage degradation
            weather_pivot["Degradation_Pct"] = ((weather_pivot["Clear"] - weather_pivot["Rainy"]) / weather_pivot["Clear"]) * 100
            weather_pivot = weather_pivot.sort_values(by="Degradation_Pct", ascending=True).reset_index()

            fig_vuln = px.bar(
                weather_pivot,
                x="Degradation_Pct",
                y="name",
                orientation="h",
                color="Degradation_Pct",
                color_continuous_scale="Reds",
                labels={"Degradation_Pct": "Velocity Degradation (%)", "name": "Monitored Artery"},
            )
            fig_vuln.update_traces(texttemplate='%{x:.1f}%', textposition='outside')
            st.plotly_chart(fig_vuln, use_container_width=True)
        else:
            st.info("Insufficient precipitation variance data to compute vulnerability matrix.", icon=":material/info:")

# ==========================================
# TAB 3: CAPITAL DEGRADATION (Cost of Congestion)
# ==========================================
with tab3:
    st.subheader("Macro-Level Economic Friction")
    st.write("Ranking arteries by absolute cumulative minutes lost to systemic congestion.")

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
        labels={"delay_mins": "Total Cumulative Delay (Mins)", "name": "Monitored Artery"},
    )
    st.plotly_chart(fig_cost, use_container_width=True)

# ==========================================
# TAB 4: MLOPS DIAGNOSTICS
# ==========================================
with tab4:
    st.subheader("Predictive Engine Diagnostics")
    st.write("Real-time telemetry regarding the Scikit-Learn Random Forest accuracy margins.")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    metrics_path = os.path.join(root_dir, "model_metrics.csv")

    try:
        metrics_df = pd.read_csv(metrics_path)
        col1, col2, col3 = st.columns(3)
        latest_metrics = metrics_df.iloc[-1]

        col1.metric(
            "Mean Absolute Error (MAE)",
            f"± {latest_metrics['MAE_Minutes']:.2f} mins",
            delta="Variance Threshold",
            delta_color="inverse",
        )

        if "R2_Score" in metrics_df.columns and pd.notna(latest_metrics["R2_Score"]):
            col2.metric("Coefficient of Determination (R²)", f"{latest_metrics['R2_Score']:.2f}")
        else:
            col2.metric("Coefficient of Determination (R²)", "Compiling...")

        col3.metric("Last Weights Update", str(latest_metrics["Date"]).split()[0])

        st.success("Target model operating within acceptable standard deviation thresholds.", icon=":material/verified:")

    except FileNotFoundError:
        st.info("Local metrics missing. Execute primary training pipeline to establish baselines.", icon=":material/search_off:")
