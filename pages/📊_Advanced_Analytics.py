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
                for rain_word in ["rain", "drizzle", "shower", "storm", "thunder"]
            ):
                return "Rainy"
            elif any(cloud_word in w for cloud_word in ["cloud", "overcast"]):
                return "Cloudy"
            else:
                return "Clear"

        if "weather" in df.columns:
            df["Condition"] = df["weather"].apply(map_weather)
        else:
            df["Condition"] = "Clear"

    return df


# --- 4. LOAD DATA ---
with st.spinner("Compiling historical telemetry datasets..."):
    df = load_historical_data()

if df.empty:
    st.warning(
        "Insufficient historical telemetry. Awaiting further ingestion cycles.",
        icon=":material/warning:",
    )
    st.stop()


# ==========================================
# ENTERPRISE UI TABS
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(
    [
        ":material/timeline: Temporal Matrix",
        ":material/hub: Behavioral Clustering",
        ":material/account_balance: Economic Simulator",
        ":material/memory: ML Proof & Metrics",
    ]
)

# ------------------------------------------
# TAB 1: TEMPORAL FLOW MATRIX
# ------------------------------------------
with tab1:
    st.subheader("Temporal Congestion Distribution")
    st.caption(
        "Aggregated heatmap identifying systemic network gridlock by hour and day."
    )

    df["Clean_Hour"] = df["Hour"].astype(int)
    pivot_df = df.pivot_table(
        index="Day", columns="Clean_Hour", values="delay_mins", aggfunc="mean"
    )

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
    target_hours = list(range(6, 23))
    pivot_df = pivot_df.reindex(columns=target_hours).fillna(0)

    fig_heat = px.imshow(
        pivot_df,
        labels=dict(
            x="Operating Hour (06:00 - 23:00)",
            y="Day of Week",
            color="Mean Delay (Mins)",
        ),
        color_continuous_scale="YlOrRd",
        aspect="auto",
        height=500,
    )
    fig_heat.update_xaxes(tickmode="linear", dtick=1)
    st.plotly_chart(fig_heat, use_container_width=True)

# ------------------------------------------
# TAB 2: UNSUPERVISED BEHAVIORAL CLUSTERING
# ------------------------------------------
with tab2:
    st.subheader("K-Means Spatial DNA Profiling")
    st.caption(
        "Unsupervised AI categorization of road behavior based on severity vs. unpredictability."
    )

    cluster_data = (
        df.groupby("name")
        .agg(Mean_Delay=("delay_mins", "mean"), Volatility=("delay_mins", "std"))
        .fillna(0)
        .reset_index()
    )

    if len(cluster_data) > 3:
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(
            cluster_data[["Mean_Delay", "Volatility"]]
        )

        kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
        cluster_data["Cluster_ID"] = kmeans.fit_predict(scaled_features)

        cluster_centers = (
            cluster_data.groupby("Cluster_ID")["Mean_Delay"].mean().sort_values()
        )
        label_map = {
            cluster_centers.index[0]: "High-Velocity Corridors",
            cluster_centers.index[1]: "Rush-Hour Traps (Volatile)",
            cluster_centers.index[2]: "Chronic Gridlock Zones",
        }
        cluster_data["Profile"] = cluster_data["Cluster_ID"].map(label_map)
        color_map = {
            "High-Velocity Corridors": "#28a745",
            "Rush-Hour Traps (Volatile)": "#ffc107",
            "Chronic Gridlock Zones": "#dc3545",
        }

        fig_cluster = px.scatter(
            cluster_data,
            x="Mean_Delay",
            y="Volatility",
            color="Profile",
            hover_name="name",
            color_discrete_map=color_map,
            labels={
                "Mean_Delay": "Average Delay (Minutes)",
                "Volatility": "Unpredictability (Standard Deviation)",
            },
        )
        fig_cluster.update_traces(
            marker=dict(
                size=16, opacity=0.9, line=dict(width=1.5, color="DarkSlateGrey")
            )
        )
        fig_cluster.update_layout(
            height=550,
            hoverlabel=dict(bgcolor="#2b2b2b", font_color="white", font_size=14),
        )
        st.plotly_chart(fig_cluster, use_container_width=True)
    else:
        st.info(
            "Insufficient spatial variance to run K-Means clustering.",
            icon=":material/info:",
        )

# ------------------------------------------
# TAB 3: MACRO-ECONOMIC DRAIN SIMULATOR
# ------------------------------------------
with tab3:
    st.subheader("Annualized Capital Hemorrhage")
    st.caption(
        "Translate traffic delays directly into GDP impact using dynamic economic variables."
    )

    with st.container(border=True):
        sc1, sc2, sc3 = st.columns(3)
        wage_rate = sc1.number_input("Median Hourly Wage (TZS)", value=3500, step=500)
        fuel_cost = sc2.number_input("Fuel Cost per Liter (TZS)", value=3200, step=100)
        cars_per_hour = sc3.slider(
            "Estimated Vehicles per Node/Hour",
            min_value=100,
            max_value=2000,
            value=750,
            step=50,
        )

    idle_burn_rate_per_hr = 1.2
    cost_per_minute = (wage_rate / 60) + ((fuel_cost * idle_burn_rate_per_hr) / 60)
    annual_multiplier = 260 * 4

    cost_df = df.groupby("name")["delay_mins"].mean().reset_index()
    cost_df["Annual_Loss_TZS"] = (
        cost_df["delay_mins"] * cost_per_minute * cars_per_hour * annual_multiplier
    )
    cost_df = cost_df.sort_values(by="Annual_Loss_TZS", ascending=True)

    fig_finance = px.bar(
        cost_df,
        x="Annual_Loss_TZS",
        y="name",
        orientation="h",
        color="Annual_Loss_TZS",
        color_continuous_scale="Reds",
        labels={"Annual_Loss_TZS": "Annual Economic Drain (TZS)", "name": "Artery"},
        height=600,
    )
    st.plotly_chart(fig_finance, use_container_width=True)

# ------------------------------------------
# TAB 4: EXPLAINABLE AI (XAI) & MLOPS VALIDATION
# ------------------------------------------
with tab4:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = (
        os.path.dirname(current_dir)
        if os.path.basename(current_dir) == "pages"
        else current_dir
    )
    model_path = os.path.join(root_dir, "traffic_model.pkl")

    # TOP HALF: The Unboxing & The Metrics
    col_xai, col_metrics = st.columns([2, 1], gap="large")

    with col_xai:
        st.subheader("Unboxing the Black Box")
        st.caption(
            "Extracting the exact decision-making weights from the Random Forest model."
        )

        if os.path.exists(model_path):
            try:
                actual_model = joblib.load(model_path)
                importances, feature_names = None, None

                if hasattr(actual_model, "feature_importances_"):
                    importances = actual_model.feature_importances_
                    feature_names = getattr(
                        actual_model,
                        "feature_names_in_",
                        [f"Feature {i}" for i in range(len(importances))],
                    )
                elif hasattr(actual_model, "steps"):
                    rf_step = actual_model.steps[-1][1]
                    if hasattr(rf_step, "feature_importances_"):
                        importances = rf_step.feature_importances_
                        preprocessor = actual_model.steps[0][1]
                        if hasattr(preprocessor, "get_feature_names_out"):
                            feature_names = preprocessor.get_feature_names_out()
                        else:
                            feature_names = [
                                f"Feature {i}" for i in range(len(importances))
                            ]

                if importances is not None:
                    importance_df = pd.DataFrame(
                        {"Feature": feature_names, "Importance": importances * 100}
                    )
                    importance_df["Core_Category"] = importance_df["Feature"].apply(
                        lambda x: (
                            "Road / Artery"
                            if "road_id" in str(x)
                            else (
                                "Weather Condition"
                                if "Condition" in str(x)
                                else (
                                    "Day of Week"
                                    if "Day" in str(x)
                                    else (
                                        "Time of Day (Hour)"
                                        if "Hour" in str(x)
                                        else "Other"
                                    )
                                )
                            )
                        )
                    )
                    grouped_importance = (
                        importance_df.groupby("Core_Category")["Importance"]
                        .sum()
                        .reset_index()
                        .sort_values(by="Importance", ascending=True)
                    )

                    fig_importance = px.bar(
                        grouped_importance,
                        x="Importance",
                        y="Core_Category",
                        orientation="h",
                        labels={
                            "Importance": "Influence on Traffic Variance (%)",
                            "Core_Category": "",
                        },
                        height=280,
                    )
                    fig_importance.update_traces(marker_color="#4B8BBE")
                    st.plotly_chart(fig_importance, use_container_width=True)
                else:
                    st.warning(
                        "Could not extract feature importances from the model.",
                        icon=":material/warning:",
                    )
            except Exception as e:
                st.error(f"Failed to unbox model: {e}", icon=":material/error:")
        else:
            st.info(
                "Awaiting traffic_model.pkl to compute Explainable AI matrix.",
                icon=":material/info:",
            )

    with col_metrics:
        st.subheader("System Accuracy")
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
                "Total Training Vectors",
                f"{int(latest_metrics['Total_Rows_Trained']):,}",
            )
        except FileNotFoundError:
            st.info("Primary training metrics pending.", icon=":material/search_off:")

    st.write("")  # Spacer

    # BOTTOM HALF: The Truth Engine Validation Graph
    with st.container(border=True):
        st.subheader("AI Accuracy Engine (Predicted vs. Actual)")
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

        if os.path.exists(model_path):
            try:
                db = get_db()
                docs = (
                    db.collection("traffic_history")
                    .where("road_id", "==", test_road_id)
                    .order_by("timestamp", direction=firestore.Query.DESCENDING)
                    .limit(100)
                    .stream()
                )

                history_data = [
                    doc.to_dict() for doc in docs if "timestamp" in doc.to_dict()
                ]
                df_val = pd.DataFrame(history_data)

                if not df_val.empty:
                    df_val = df_val.sort_values("timestamp")
                    df_val["timestamp"] = pd.to_datetime(
                        df_val["timestamp"]
                    ).dt.tz_convert("Africa/Dar_es_Salaam")
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

                    model = joblib.load(model_path)
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
                        xaxis_title="Time of Day",
                        yaxis_title="Delay (Minutes)",
                        hovermode="x unified",
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1,
                        ),
                        height=350,
                        margin=dict(t=20, b=0, l=0, r=0),
                    )

                    st.plotly_chart(fig_val, use_container_width=True)
                    error_margin = abs(
                        df_val["delay_mins"] - df_val["Predicted_Delay"]
                    ).mean()
                    st.info(
                        f"**Insight:** The model is predicting traffic for this specific artery within an average variance of **±{error_margin:.1f} minutes** from physical reality."
                    )
                else:
                    st.info(
                        "Insufficient telemetry data collected for this artery to run predictive validation."
                    )
            except Exception as e:
                st.error(f"Validation Engine Offline: {e}")
