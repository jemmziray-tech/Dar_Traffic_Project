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
    page_title="Advanced Analytics", 
    page_icon=":material/analytics:", 
    layout="wide"
)

# --- 2. MODERN UI CSS INJECTION ---
st.markdown("""
<style>
    .metric-card {
        background-color: #1E1E1E;
        padding: 20px;
        border-radius: 8px;
        border-left: 4px solid #4B8BBE;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        margin-bottom: 20px;
    }
    .metric-title { color: #A0A0A0; font-size: 0.85rem; text-transform: uppercase; font-weight: 600; margin-bottom: 5px; letter-spacing: 0.5px;}
    .metric-value { color: #FFFFFF; font-size: 1.8rem; font-weight: bold; margin: 0;}
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: transparent; border-radius: 4px 4px 0px 0px; gap: 1px; padding-top: 10px; padding-bottom: 10px; }
    .stTabs [aria-selected="true"] { border-bottom: 2px solid #4B8BBE; color: #4B8BBE; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

st.title(":material/query_stats: Enterprise Traffic Intelligence")
st.markdown("<p style='color:#A0A0A0; font-size: 1.1rem; margin-bottom: 2rem;'>Deep-dive business intelligence, spatial clustering, and ML validation analysis.</p>", unsafe_allow_html=True)

# --- 3. SECURE FIREBASE CONNECTION ---
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

# --- 4. DATA FETCHING & V3 TRANSLATION LAYER ---
@st.cache_data(ttl=600)
def load_historical_data():
    db = get_db()
    docs = db.collection("traffic_history").stream()
    df = pd.DataFrame([doc.to_dict() for doc in docs])

    if df.empty:
        return df

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    if df["timestamp"].dt.tz is None:
        df["timestamp"] = df["timestamp"].dt.tz_localize("UTC").dt.tz_convert("Africa/Dar_es_Salaam")
    else:
        df["timestamp"] = df["timestamp"].dt.tz_convert("Africa/Dar_es_Salaam")

    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["is_weekend"] = df["day_of_week"].apply(lambda x: 1 if x >= 5 else 0)
    df["is_rush_hour"] = df["hour"].apply(lambda x: 1 if x in [7, 8, 16, 17, 18, 19] else 0)

    day_map = {0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun'}
    df['Day_Name'] = df['day_of_week'].map(day_map)

    df["temp_c"] = df["weather"].astype(str).str.extract(r'([0-9.]+)').astype(float)
    df["temp_c"] = df["temp_c"].fillna(25.0) 
    df["condition"] = df["weather"].apply(lambda x: str(x).split(", ")[1] if ", " in str(x) else "Clear")
    df["is_raining"] = df["condition"].apply(lambda x: 1 if "Rain" in str(x) else 0)

    df = df.sort_values(by=["road_id", "timestamp"])
    df["previous_delay"] = df.groupby("road_id")["delay_mins"].shift(1)
    df["delay_velocity"] = df["delay_mins"] - df["previous_delay"]
    df["delay_velocity"] = df["delay_velocity"].fillna(0) 

    return df

df = load_historical_data()

if df.empty:
    st.error(":material/warning: No telemetry data found in the database. Please check your data pipeline.")
    st.stop()

# --- 5. GLOBAL KPI CARDS ---
kpi1, kpi2, kpi3 = st.columns(3)
with kpi1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Total Telemetry Points</div>
        <div class="metric-value">{len(df):,}</div>
    </div>
    """, unsafe_allow_html=True)
with kpi2:
    st.markdown(f"""
    <div class="metric-card" style="border-left-color: #F6C85F;">
        <div class="metric-title">City-Wide Avg Delay</div>
        <div class="metric-value">{df['delay_mins'].mean():.1f} mins</div>
    </div>
    """, unsafe_allow_html=True)
with kpi3:
    worst_road = df.groupby('road_id')['delay_mins'].mean().idxmax()
    st.markdown(f"""
    <div class="metric-card" style="border-left-color: #FF4B4B;">
        <div class="metric-title">Primary Bottleneck</div>
        <div class="metric-value">{worst_road.replace('_', ' ').title()}</div>
    </div>
    """, unsafe_allow_html=True)


# --- 6. TABBED NAVIGATION ARCHITECTURE ---
tab_overview, tab_dynamics, tab_validation, tab_mlops = st.tabs([
    ":material/dashboard: Overview", 
    ":material/insights: Traffic Dynamics", 
    ":material/fact_check: ML Validation",
    ":material/monitoring: MLOps & Drift"
])

# ==========================================
# TAB 1: OVERVIEW (The Heatmap)
# ==========================================
with tab_overview:
    st.subheader(":material/calendar_view_week: Temporal Congestion Matrix")
    st.markdown("<p style='color:#A0A0A0; font-size: 0.9rem;'>Visualizing Dar es Salaam gridlock patterns during active operational hours (06:00 - 22:00).</p>", unsafe_allow_html=True)

    heat_df = df.groupby(['Day_Name', 'hour'])['delay_mins'].mean().reset_index()
    heat_df = heat_df[(heat_df['hour'] >= 6) & (heat_df['hour'] <= 22)]
    heat_df['Hour_Label'] = heat_df['hour'].apply(lambda x: f"{x:02d}:00")

    day_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    hour_order = [f"{h:02d}:00" for h in range(6, 23)]

    fig_heat = px.density_heatmap(
        heat_df, x="Hour_Label", y="Day_Name", z="delay_mins",
        histfunc="avg", color_continuous_scale="RdYlGn_r", 
        category_orders={"Day_Name": day_order[::-1], "Hour_Label": hour_order}, 
        labels={"Hour_Label": "Time of Day", "Day_Name": "Day of Week", "delay_mins": "Avg Delay (Mins)"}
    )
    
    fig_heat.update_layout(
        template="plotly_dark", height=450, margin=dict(t=20, b=20, l=0, r=0),
        xaxis=dict(side="bottom", tickangle=0, showgrid=False, title_font=dict(color="#A0A0A0"), tickfont=dict(color="#E0E0E0")),
        yaxis=dict(showgrid=False, title_font=dict(color="#A0A0A0"), tickfont=dict(color="#E0E0E0", size=13)),
        coloraxis_colorbar=dict(title="Delay", thicknessmode="pixels", thickness=12, lenmode="pixels", len=300, yanchor="middle", y=0.5, tickfont=dict(color="#A0A0A0"))
    )
    st.plotly_chart(fig_heat, use_container_width=True)

# ==========================================
# TAB 2: TRAFFIC DYNAMICS (Upgraded)
# ==========================================
with tab_dynamics:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader(":material/moving: Gridlock Trend (Rate of Change)")
        st.markdown("<p style='color:#A0A0A0; font-size: 0.9rem;'>Shows if congestion is actively building up (Red) or clearing out (Green) at any given hour.</p>", unsafe_allow_html=True)
        
        # Calculate momentum and assign clear human categories
        momentum_df = df.groupby("hour")["delay_velocity"].mean().reset_index()
        momentum_df = momentum_df[(momentum_df['hour'] >= 6) & (momentum_df['hour'] <= 22)]
        momentum_df["Trend_State"] = momentum_df["delay_velocity"].apply(lambda x: "Worsening (Building)" if x > 0 else "Clearing (Recovering)")
        momentum_df['Hour_Label'] = momentum_df['hour'].apply(lambda x: f"{x:02d}:00")

        fig_vel = px.bar(
            momentum_df, x="Hour_Label", y="delay_velocity", color="Trend_State",
            color_discrete_map={"Worsening (Building)": "#FF4B4B", "Clearing (Recovering)": "#00CC96"},
            labels={"delay_velocity": "Change in Delay (Mins)", "Hour_Label": "Time of Day"}
        )
        # Add a white horizontal line at 0 to make the split obvious
        fig_vel.add_hline(y=0, line_width=2, line_color="white")
        fig_vel.update_layout(template="plotly_dark", height=400, margin=dict(t=20, b=0, l=0, r=0), showlegend=False)
        st.plotly_chart(fig_vel, use_container_width=True)

    with col2:
        st.subheader(":material/bubble_chart: Traffic State Clusters")
        st.markdown("<p style='color:#A0A0A0; font-size: 0.9rem;'>AI automatically groups historical data into three distinct traffic severities.</p>", unsafe_allow_html=True)
        
        cluster_data = df[["hour", "delay_mins", "temp_c"]].dropna()
        if len(cluster_data) >= 3:
            # Run the AI
            kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
            raw_labels = kmeans.fit_predict(cluster_data)
            
            # THE FIX: Mathematically map the random cluster numbers to human concepts based on delay severity
            cluster_data['Raw_Cluster'] = raw_labels
            cluster_means = cluster_data.groupby('Raw_Cluster')['delay_mins'].mean().sort_values()
            
            # The lowest mean is Free Flow, highest is Severe Gridlock
            label_mapping = {
                cluster_means.index[0]: "Smooth Flow (Optimal)",
                cluster_means.index[1]: "Moderate Congestion",
                cluster_means.index[2]: "Severe Gridlock (Critical)"
            }
            
            df.loc[cluster_data.index, "Traffic_State"] = cluster_data['Raw_Cluster'].map(label_mapping)
            
            # Explicitly force colors to match the concepts
            color_map = {
                "Smooth Flow (Optimal)": "#00CC96",  # Green
                "Moderate Congestion": "#F6C85F",    # Yellow
                "Severe Gridlock (Critical)": "#FF4B4B" # Red
            }

            fig_cluster = px.scatter(
                df, x="hour", y="delay_mins", color="Traffic_State",
                color_discrete_map=color_map,
                labels={"hour": "Hour of Day", "delay_mins": "Total Delay (Mins)", "Traffic_State": "AI State Classification"}
            )
            fig_cluster.update_layout(
                template="plotly_dark", height=400, margin=dict(t=20, b=0, l=0, r=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_cluster, use_container_width=True)

# ==========================================
# TAB 3: ML VALIDATION ENGINE
# ==========================================
with tab_validation:
    st.subheader(":material/model_training: XGBoost Validation Engine")
    st.markdown("<p style='color:#A0A0A0; font-size: 0.9rem;'>Auditing the AI's predictive math against live historical reality.</p>", unsafe_allow_html=True)

    model_path = "traffic_model.pkl"
    if os.path.exists(model_path):
        try:
            model = joblib.load(model_path)
            target_road = st.selectbox("Select Artery for Validation Audit:", df["road_id"].unique())
            df_val = df[df["road_id"] == target_road].sort_values("timestamp").copy()
            
            if not df_val.empty:
                features = ["road_id", "hour", "day_of_week", "is_weekend", "is_rush_hour", "temp_c", "is_raining", "delay_velocity"]
                df_val["Predicted_Delay"] = model.predict(df_val[features])
                df_val["Predicted_Delay"] = df_val["Predicted_Delay"].clip(lower=0)

                fig_val = go.Figure()
                fig_val.add_trace(go.Scatter(
                    x=df_val["timestamp"], y=df_val["delay_mins"], 
                    mode="lines", name="Actual Delay (Reality)", line=dict(color="#FF4B4B", width=2)
                ))
                fig_val.add_trace(go.Scatter(
                    x=df_val["timestamp"], y=df_val["Predicted_Delay"], 
                    mode="lines", name="AI Prediction", line=dict(color="#00CC96", width=2, dash="dash")
                ))
                
                fig_val.update_layout(
                    template="plotly_dark", height=400, hovermode="x unified",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    margin=dict(t=20, b=0, l=0, r=0)
                )
                st.plotly_chart(fig_val, use_container_width=True)
                
                error_margin = abs(df_val["delay_mins"] - df_val["Predicted_Delay"]).mean()
                st.info(f":material/lightbulb: **Audit Insight:** The XGBoost Engine predicts traffic for **{target_road}** with an average absolute variance of **±{error_margin:.1f} minutes** from physical reality.", icon="ℹ️")
        except Exception as e:
            st.error(f":material/error: Validation Engine Offline: {e}")
    else:
        st.warning(":material/warning: V3 traffic_model.pkl not found. Train the model first.")

# ==========================================
# TAB 4: MLOps & DRIFT TRACKING
# ==========================================
with tab_mlops:
    st.subheader(":material/monitoring: MLOps Performance Drift")
    st.markdown("<p style='color:#A0A0A0; font-size: 0.9rem;'>Tracking the AI model's accuracy (R²) and error rate (MAE) as the training dataset grows over time.</p>", unsafe_allow_html=True)

    metrics_path = "model_metrics.csv"
    if os.path.exists(metrics_path):
        try:
            df_metrics = pd.read_csv(metrics_path)
            df_metrics["Date"] = pd.to_datetime(df_metrics["Date"])

            col1, col2 = st.columns(2)

            with col1:
                fig_r2 = px.area(
                    df_metrics, x="Date", y="R2_Score", 
                    title="Model Accuracy (R² Score) over Time",
                    markers=True, color_discrete_sequence=["#00CC96"]
                )
                fig_r2.update_layout(template="plotly_dark", height=350, margin=dict(t=30, b=0, l=0, r=0))
                fig_r2.update_yaxes(range=[0.4, 1.0]) 
                st.plotly_chart(fig_r2, use_container_width=True)

            with col2:
                fig_mae = px.scatter(
                    df_metrics, x="Total_Rows_Trained", y="MAE_Minutes",
                    title="Mean Absolute Error vs. Data Volume",
                    color="R2_Score", color_continuous_scale="Viridis"
                )
                fig_mae.update_layout(template="plotly_dark", height=350, margin=dict(t=30, b=0, l=0, r=0))
                st.plotly_chart(fig_mae, use_container_width=True)

            st.info(":material/info: **Note on MAE:** A slight increase in MAE alongside a high R² score indicates the model is successfully learning to predict rare, extreme gridlock events (outliers) rather than just guessing the average.")

        except Exception as e:
            st.error(f"Error loading MLOps metrics: {e}")
    else:
        st.warning(":material/warning: model_metrics.csv not found. Metrics will populate after the next training cycle.")
