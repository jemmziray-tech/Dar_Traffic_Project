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
from sklearn.preprocessing import StandardScaler
import joblib

# --- 1. SETUP PAGE CONFIG ---
st.set_page_config(
    page_title="Advanced Analytics", page_icon=":material/analytics:", layout="wide"
)

st.title(":material/query_stats: Enterprise Traffic Intelligence")
st.markdown(
    "Deep-dive business intelligence, unsupervised spatial clustering, and macro-economic impact analysis."
)
st.divider()


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
        df["datetime"] = pd.to_datetime(df["datetime"], utc=True).dt.tz_convert(
            "Africa/Dar_es_Salaam"
        )
        df["Hour"] = df["datetime"].dt.hour
        df["Day"] = df["datetime"].dt.day_name()

        def map_weather(w):
            w = str(w).lower()
            if any(
                rain_word in w
                for rain_word in ["rain", "drizzle", "thunderstorm", "showers"]
            ):
                return "Rainy"
            elif any(cloud_word in w for cloud_word in ["cloud", "overcast"]):
                return "Cloudy"
            return "Clear"

        if "weather" in df.columns:
            df["Condition"] = df["weather"].apply(map_weather)
        else:
            df["Condition"] = "Clear"

    return df


with st.spinner("Compiling Intelligence Matrix..."):
    df_raw = load_historical_data()

if df_raw.empty:
    st.warning(
        "Telemetry Vault is currently empty. Awaiting autonomous scraper data.",
        icon=":material/hourglass_empty:",
    )
    st.stop()

# --- 4. DATA ENGINEERING & AGGREGATION ---
road_stats = (
    df_raw.groupby("name")
    .agg(
        Avg_Delay=("delay_mins", "mean"),
        Volatility=("delay_mins", "std"),
        Max_Delay=("delay_mins", "max"),
        Data_Points=("delay_mins", "count"),
    )
    .reset_index()
)

road_stats["Volatility"] = road_stats["Volatility"].fillna(0)
road_stats = road_stats[road_stats["Data_Points"] > 5]

if len(road_stats) < 3:
    st.info(
        "Gathering more spatial variance data to run clustering algorithms...",
        icon=":material/science:",
    )
    st.stop()

# --- 5. UNSUPERVISED MACHINE LEARNING (K-MEANS) ---
scaler = StandardScaler()
X_scaled = scaler.fit_transform(road_stats[["Avg_Delay", "Volatility"]])

kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
road_stats["Cluster"] = kmeans.fit_predict(X_scaled)

cluster_centers = road_stats.groupby("Cluster")["Avg_Delay"].mean().sort_values()
cluster_mapping = {
    cluster_centers.index[0]: "High-Velocity Corridors",
    cluster_centers.index[1]: "Rush-Hour Traps",
    cluster_centers.index[2]: "Chronic Gridlock Zones",
}
road_stats["Artery_Classification"] = road_stats["Cluster"].map(cluster_mapping)

color_discrete_map = {
    "High-Velocity Corridors": "#2ecc71",
    "Rush-Hour Traps": "#f1c40f",
    "Chronic Gridlock Zones": "#e74c3c",
}

# --- 6. MACRO-ECONOMIC IMPACT CALCULATOR ---
st.subheader(":material/account_balance: Economic Friction Analysis")
st.caption(
    "Quantifying the financial drain of urban congestion using standard capital burn rates."
)

with st.container(border=True):
    col_c1, col_c2, col_c3 = st.columns(3)

    cost_per_min = col_c1.number_input(
        "TZS Wasted per Minute (Idle Cost)",
        value=101,
        step=10,
        help="Average fuel and productivity cost per minute.",
    )
    cars_per_road = col_c2.number_input(
        "Average Vehicles per Artery",
        value=750,
        step=50,
        help="Estimated standing volume of commercial and private vehicles.",
    )
    selected_road = col_c3.selectbox(
        "Analyze Specific Infrastructure", road_stats["name"].sort_values()
    )

    road_data = road_stats[road_stats["name"] == selected_road].iloc[0]
    avg_delay = road_data["Avg_Delay"]
    daily_cost = avg_delay * cars_per_road * cost_per_min
    monthly_cost = daily_cost * 22

    st.write("")
    m1, m2, m3 = st.columns(3)
    m1.metric(
        "Average Delay",
        f"{avg_delay:.1f} Mins",
        delta=road_data["Artery_Classification"],
        delta_color="off",
    )
    m2.metric("Daily Economic Bleed", f"TZS {int(daily_cost):,}")
    m3.metric(
        "Monthly Capital Friction",
        f"TZS {int(monthly_cost):,}",
        delta="Lost Productivity",
        delta_color="inverse",
    )

st.divider()

# --- 7. SPATIAL CLUSTERING VISUALIZATION ---
st.subheader(":material/scatter_plot: Infrastructure Volatility Matrix (K-Means)")
st.caption(
    "AI-driven classification of roads based on mean congestion vs. behavioral unpredictability."
)

road_stats_sorted = road_stats.sort_values("Avg_Delay", ascending=True)

fig = go.Figure()
for classification in [
    "High-Velocity Corridors",
    "Rush-Hour Traps",
    "Chronic Gridlock Zones",
]:
    subset = road_stats_sorted[
        road_stats_sorted["Artery_Classification"] == classification
    ]
    if not subset.empty:
        fig.add_trace(
            go.Bar(
                y=subset["name"],
                x=subset["Avg_Delay"],
                orientation="h",
                name=classification,
                marker_color=color_discrete_map[classification],
                error_x=dict(
                    type="data",
                    array=subset["Volatility"],
                    visible=True,
                    color="rgba(255,255,255,0.4)",
                ),
            )
        )

fig.update_layout(
    template="plotly_dark",
    barmode="group",
    height=600,
    xaxis_title="Average Delay (Minutes) ± Standard Deviation",
    yaxis_title="",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- 8. EXPLAINABLE AI (UNBOXING THE MODEL) ---
col_feat, col_metrics = st.columns([2, 1], gap="large")

root_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(root_dir) == "pages":
    root_dir = os.path.dirname(root_dir)

with col_feat:
    st.subheader(":material/memory: Explaining the Black Box")
    st.caption("Feature Importance: How the Scikit-Learn model weights decision nodes.")

    model_path = os.path.join(root_dir, "traffic_model.pkl")

    if os.path.exists(model_path):
        try:
            model = joblib.load(model_path)

            if hasattr(model, "feature_importances_"):
                importances = model.feature_importances_

                # Dynamic matching based on feature count
                if len(importances) == 4:
                    feature_names = [
                        "Artery ID",
                        "Hour of Day",
                        "Day of Week",
                        "Meteorological Condition",
                    ]
                elif len(importances) == 3:
                    feature_names = ["Artery ID", "Hour of Day", "Day of Week"]
                else:
                    feature_names = [f"Vector {i}" for i in range(len(importances))]

                feat_df = pd.DataFrame(
                    {"Feature": feature_names, "Importance": importances}
                )
                feat_df = feat_df.sort_values(by="Importance", ascending=True)

                fig_importance = px.bar(
                    feat_df,
                    x="Importance",
                    y="Feature",
                    orientation="h",
                    template="plotly_dark",
                    height=250,
                )
                fig_importance.update_traces(marker_color="#4B8BBE")
                st.plotly_chart(fig_importance, use_container_width=True)

            else:
                st.warning(
                    "Model loaded, but could not extract feature importances. Ensure it is a Tree-based model.",
                    icon=":material/warning:",
                )

        except Exception as e:
            st.error(f"Failed to unbox model: {e}", icon=":material/error:")
    else:
        st.info(
            "Awaiting traffic_model.pkl in the root directory to compute Explainable AI matrix.",
            icon=":material/info:",
        )

with col_metrics:
    st.subheader(":material/speed: System Accuracy")
    st.caption("Real-time pipeline verification.")

    metrics_path = os.path.join(root_dir, "model_metrics.csv")

    try:
        metrics_df = pd.read_csv(metrics_path)
        latest_metrics = metrics_df.iloc[-1]

        st.metric(
            "Mean Absolute Error",
            f"± {latest_metrics['MAE_Minutes']:.2f} mins",
            delta="Operational",
            delta_color="normal",
        )

        if "R2_Score" in metrics_df.columns:
            st.metric(
                "R² Confidence Score",
                f"{latest_metrics['R2_Score']:.2f}",
                delta="Validated",
                delta_color="normal",
            )

        st.metric(
            "Total Training Vectors", f"{int(latest_metrics['Total_Rows_Trained']):,}"
        )
    except FileNotFoundError:
        st.info(
            "Primary training metrics pending. Run core ML pipeline.",
            icon=":material/search_off:",
        )


# --- 9. THE TRUTH ENGINE (PREDICTED VS. ACTUAL VALIDATION) ---
st.divider()
st.subheader(":material/query_stats: AI Accuracy Engine (Predicted vs. Actual)")
st.caption(
    "Validating the Random Forest model's predictions against real-world historical telemetry."
)

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
REVERSE_ROAD_MAP = {v: k for k, v in ROAD_MAP.items()}

test_road_name = st.selectbox(
    "Select Infrastructure to Validate", list(ROAD_MAP.values()), index=2
)
test_road_id = REVERSE_ROAD_MAP[test_road_name]

with st.spinner("Fetching historical validation data from Cloud Vault..."):
    try:
        if "model" not in locals():
            model = joblib.load(os.path.join(root_dir, "traffic_model.pkl"))

        db = get_db()
        docs = (
            db.collection("traffic_history")
            .where("road_id", "==", test_road_id)
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(150)
            .stream()
        )

        history_data = []
        for doc in docs:
            doc_dict = doc.to_dict()
            if "timestamp" in doc_dict:
                history_data.append(doc_dict)

        df_val = pd.DataFrame(history_data)

        if not df_val.empty:
            df_val = df_val.sort_values("timestamp")

            # Dynamic Feature Engineering
            df_val["timestamp"] = pd.to_datetime(df_val["timestamp"]).dt.tz_convert(
                "Africa/Dar_es_Salaam"
            )
            df_val["Readable_Time"] = df_val["timestamp"].dt.strftime("%H:%M")
            df_val["Hour"] = df_val["timestamp"].dt.hour + (
                df_val["timestamp"].dt.minute / 60.0
            )
            df_val["Day"] = df_val["timestamp"].dt.day_name()

            pred_features = pd.DataFrame(
                {
                    "road_id": df_val["road_id"],
                    "Hour": df_val["Hour"],
                    "Day": df_val["Day"],
                    "Condition": df_val["weather"],
                }
            )

            df_val["Predicted_Delay"] = model.predict(pred_features)

            fig_val = go.Figure()

            fig_val.add_trace(
                go.Scatter(
                    x=df_val["Readable_Time"],
                    y=df_val["delay_mins"],
                    mode="lines+markers",
                    name="Actual Traffic Delay",
                    line=dict(color="#e74c3c", width=3),
                    marker=dict(size=6),
                )
            )

            fig_val.add_trace(
                go.Scatter(
                    x=df_val["Readable_Time"],
                    y=df_val["Predicted_Delay"],
                    mode="lines",
                    name="AI Predicted Delay",
                    line=dict(color="#4B8BBE", width=3, dash="dash"),
                )
            )

            fig_val.update_layout(
                template="plotly_dark",
                title=f"Predictive Engine Accuracy: {test_road_name}",
                xaxis_title="Time of Day",
                yaxis_title="Delay (Minutes)",
                hovermode="x unified",
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
                ),
                height=400,
            )

            st.plotly_chart(fig_val, use_container_width=True)

            error_margin = abs(df_val["delay_mins"] - df_val["Predicted_Delay"]).mean()
            st.caption(
                f"**Mean Absolute Error (MAE):** The Intelligence Matrix is predicting traffic on this route within an average variance of **±{error_margin:.1f} minutes** from physical reality."
            )

        else:
            st.info(
                "Insufficient telemetry data collected for this artery to run predictive validation.",
                icon=":material/info:",
            )

    except Exception as e:
        st.error(
            f"Validation Engine Offline: Ensure model is trained and data exists. ({e})",
            icon=":material/error:",
        )
