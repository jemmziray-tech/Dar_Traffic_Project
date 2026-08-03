import os
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# --- 1. Setup Page Config ---
st.set_page_config(
    page_title="Route History", layout="wide", page_icon=":material/history:"
)

# --- CUSTOM CSS ---
st.markdown(
    """
<style>
div[data-testid="stMetricValue"] { font-weight: 600; letter-spacing: -0.5px; }
.block-container { padding-top: 2rem; padding-bottom: 2rem; }
</style>
""",
    unsafe_allow_html=True,
)


# --- 2. Connect to Firebase ---
@st.cache_resource
def get_db():
    if not firebase_admin._apps:
        try:
            if os.path.exists("firebase-key.json"):
                cred = credentials.Certificate("firebase-key.json")
            elif "firebase" in st.secrets:
                key_dict = json.loads(st.secrets["firebase"]["key_data"])
                cred = credentials.Certificate(key_dict)
            else:
                st.error("No valid Firebase credentials found.", icon=":material/lock:")
                st.stop()
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Failed to connect: {e}", icon=":material/error:")
            st.stop()
    return firestore.client()


db = get_db()


# --- 3. Functions ---
@st.cache_data(ttl=300)
def get_roads_list():
    docs = db.collection("live_traffic").stream()
    return sorted([doc.id for doc in docs])


@st.cache_data(ttl=300)
def get_historical_data(road_id):
    stats_ref = db.collection("traffic_history")
    query = (
        stats_ref.where("road_id", "==", road_id)
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(20000)  # Deep enough for solid trends, light enough for fast UI
    )
    results = query.stream()
    return pd.DataFrame([doc.to_dict() for doc in results])


def format_road_name(r_id):
    return str(r_id).replace("_", " ").title()


def map_weather(w):
    """Safely categorizes weather without deleting rows"""
    w = str(w).lower()
    if any(r in w for r in ["rain", "drizzle", "storm", "shower"]):
        return "Rainy"
    if any(c in w for c in ["cloud", "overcast"]):
        return "Cloudy"
    return "Clear"


# --- 4. Main UI Header ---
st.title(":material/route: Route Telemetry & History")
st.caption("Deep historical analysis and forecasting for individual city arteries.")
st.divider()

# ROAD SELECTOR (Moved to main body for better UX)
roads = get_roads_list()
selected_road = st.selectbox(
    "Select Target Artery",
    roads,
    format_func=format_road_name,
    label_visibility="collapsed",
)

if selected_road:
    with st.spinner(f"Pulling telemetry for {format_road_name(selected_road)}..."):
        hist_df = get_historical_data(selected_road)

    if not hist_df.empty:
        # Timezone safety parsing
        hist_df["timestamp"] = pd.to_datetime(
            hist_df["timestamp"], utc=True
        ).dt.tz_convert("Africa/Dar_es_Salaam")
        hist_df = hist_df.sort_values("timestamp")  # Ensure chronological order

        # --- LIVE PULSE METRICS ---
        latest_record = hist_df.iloc[-1]
        current_delay = latest_record["delay_mins"]
        current_time = latest_record["timestamp"]
        current_day = current_time.day_name()
        current_hour = current_time.hour
        current_status = latest_record["status"]

        historical_matches = hist_df[
            (hist_df["timestamp"].dt.day_name() == current_day)
            & (hist_df["timestamp"].dt.hour == current_hour)
        ]
        historical_avg = (
            historical_matches["delay_mins"].mean()
            if not historical_matches.empty
            else current_delay
        )
        delay_delta = current_delay - historical_avg

        st.subheader(f"{format_road_name(selected_road)}")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Live Status", current_status)
        m2.metric(
            "Current Delay",
            f"{current_delay:.1f} Mins",
            delta=f"{delay_delta:.1f}m vs {current_hour:02d}:00 Avg",
            delta_color="off" if delay_delta == 0 else "inverse",
        )
        m3.metric("Historical Avg (This Hour)", f"{historical_avg:.1f} Mins")
        m4.metric("Last Sensor Sync", current_time.strftime("%H:%M"))

        st.write("")

        # --- TABBED INTERFACE ---
        tab_trends, tab_opt, tab_env = st.tabs(
            [
                ":material/trending_up: Live Trends & Forecast",
                ":material/schedule: Commute Optimizer",
                ":material/thermostat: Environmental Impact",
            ]
        )

        # ==========================================
        # TAB 1: TRENDS & FORECAST
        # ==========================================
        with tab_trends:
            col_chart, col_forecast = st.columns([2, 1])

            with col_chart:
                st.markdown("**7-Day Congestion Volume (With Rolling Average)**")

                # Plotly Area Chart with Rolling Average for professional smoothing
                hist_df["Rolling_Avg"] = (
                    hist_df["delay_mins"].rolling(window=12, min_periods=1).mean()
                )

                fig_area = go.Figure()
                fig_area.add_trace(
                    go.Scatter(
                        x=hist_df["timestamp"],
                        y=hist_df["delay_mins"],
                        fill="tozeroy",
                        mode="none",
                        fillcolor="rgba(220, 53, 69, 0.2)",
                        name="Raw Delay",
                    )
                )
                fig_area.add_trace(
                    go.Scatter(
                        x=hist_df["timestamp"],
                        y=hist_df["Rolling_Avg"],
                        mode="lines",
                        line=dict(color="#dc3545", width=2),
                        name="Trendline",
                    )
                )

                fig_area.update_layout(
                    template="plotly_dark",
                    height=350,
                    margin=dict(l=0, r=0, t=10, b=0),
                    xaxis_title="",
                    yaxis_title="Minutes",
                    showlegend=False,
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor="#333333"),
                )
                st.plotly_chart(fig_area, use_container_width=True)

            with col_forecast:
                st.markdown("**12-Hour Statistical Forecast**")

                # Prepare forecast data
                df_heat = hist_df[
                    (hist_df["timestamp"].dt.hour >= 6)
                    & (hist_df["timestamp"].dt.hour <= 23)
                ].copy()
                df_heat["Hour"], df_heat["Day"] = (
                    df_heat["timestamp"].dt.hour,
                    df_heat["timestamp"].dt.day_name(),
                )
                heatmap_data = (
                    df_heat.groupby(["Day", "Hour"])["delay_mins"].mean().reset_index()
                )

                if not heatmap_data.empty:
                    now = pd.Timestamp.now(tz="Africa/Dar_es_Salaam")
                    future_times = [now + pd.Timedelta(hours=i) for i in range(13)]
                    future_df = pd.DataFrame(
                        {
                            "timestamp": future_times,
                            "Day": [t.day_name() for t in future_times],
                            "Hour": [t.hour for t in future_times],
                        }
                    )
                    forecast_df = pd.merge(
                        future_df, heatmap_data, on=["Day", "Hour"], how="left"
                    ).fillna(0)
                    forecast_df["time_label"] = forecast_df["timestamp"].apply(
                        lambda t: t.strftime("%H:00")
                    )

                    fig_forecast = px.line(
                        forecast_df,
                        x="time_label",
                        y="delay_mins",
                        template="plotly_dark",
                        height=350,
                    )
                    fig_forecast.update_traces(line_color="#00d2ff", fill="tozeroy")
                    fig_forecast.update_layout(
                        margin=dict(l=0, r=0, t=10, b=0),
                        xaxis_title="",
                        yaxis_title="Predicted Mins",
                        xaxis=dict(showgrid=False),
                        yaxis=dict(showgrid=True, gridcolor="#333333"),
                    )
                    st.plotly_chart(fig_forecast, use_container_width=True)

        # ==========================================
        # TAB 2: COMMUTE OPTIMIZER
        # ==========================================
        with tab_opt:
            if not heatmap_data.empty:
                col_heat, col_shift = st.columns([2, 1])

                with col_heat:
                    st.markdown("**Historical Congestion Matrix (06:00 - 23:00)**")
                    days_order = [
                        "Monday",
                        "Tuesday",
                        "Wednesday",
                        "Thursday",
                        "Friday",
                        "Saturday",
                        "Sunday",
                    ]
                    pivot_data = heatmap_data.pivot(
                        index="Day", columns="Hour", values="delay_mins"
                    ).reindex(days_order)
                    active_hours = list(range(6, 24))
                    pivot_data = pivot_data.reindex(columns=active_hours).fillna(0)

                    # 🚨 THE FIX: Auto-Scaling Heatmap for the Individual Road
                    max_delay_for_road = pivot_data.max().max()
                    fig_heatmap = px.imshow(
                        pivot_data,
                        x=[f"{h:02d}:00" for h in active_hours],
                        y=pivot_data.index,
                        color_continuous_scale="YlOrRd",
                        aspect="auto",
                        template="plotly_dark",
                        height=350,
                        zmax=(
                            max_delay_for_road if max_delay_for_road > 0 else 1
                        ),  # Auto-adjusts the Dark Red peak!
                    )
                    fig_heatmap.update_traces(
                        xgap=2,
                        ygap=2,
                        hovertemplate="<b>%{y} at %{x}</b><br>Average Delay: %{z:.1f} mins<extra></extra>",
                    )
                    fig_heatmap.update_layout(
                        margin=dict(l=0, r=0, t=10, b=0), coloraxis_showscale=False
                    )
                    st.plotly_chart(fig_heatmap, use_container_width=True)

                with col_shift:
                    st.markdown("**Time-Shift Optimizer**")
                    with st.container(border=True):
                        target_day = st.selectbox(
                            "Travel Day", days_order, label_visibility="collapsed"
                        )
                        target_hour_str = st.selectbox(
                            "Planned Departure",
                            [f"{h:02d}:00" for h in active_hours],
                            index=2,
                            label_visibility="collapsed",
                        )
                        target_hour_int = int(target_hour_str.split(":")[0])

                        day_data = heatmap_data[heatmap_data["Day"] == target_day]

                        if not day_data.empty:

                            def get_delay(h):
                                s = day_data[day_data["Hour"] == h]["delay_mins"]
                                return s.values[0] if not s.empty else 0

                            planned_delay = get_delay(target_hour_int)
                            early_delay = get_delay(target_hour_int - 1)
                            late_delay = get_delay(target_hour_int + 1)

                            best_alt, time_saved, alt_time_str = None, 0, ""

                            if target_hour_int - 1 >= 6 and early_delay < planned_delay:
                                best_alt, time_saved, alt_time_str = (
                                    "earlier",
                                    planned_delay - early_delay,
                                    f"{target_hour_int - 1:02d}:00",
                                )

                            if (
                                target_hour_int + 1 <= 23
                                and late_delay < planned_delay
                                and (planned_delay - late_delay) > time_saved
                            ):
                                best_alt, time_saved, alt_time_str = (
                                    "later",
                                    planned_delay - late_delay,
                                    f"{target_hour_int + 1:02d}:00",
                                )

                            if best_alt and time_saved > 0.5:
                                st.success(
                                    f"**Pro Tip:** Shift to **{alt_time_str}** to avoid peak congestion and save **{time_saved:.1f} mins**.",
                                    icon=":material/tips_and_updates:",
                                )
                            else:
                                st.info(
                                    f"**{target_hour_str}** is an optimal time. Adjusting by an hour won't save significant time.",
                                    icon=":material/task_alt:",
                                )

        # ==========================================
        # TAB 3: ENVIRONMENTAL IMPACT
        # ==========================================
        with tab_env:
            col_box, col_pie = st.columns([2, 1])

            with col_box:
                st.markdown("**Meteorological Impact on Velocity**")

                # Apply the safe weather mapping function
                hist_df["Clean_Weather"] = hist_df["weather"].apply(map_weather)

                fig_speed = px.box(
                    hist_df,
                    x="speed_kmh",
                    y="Clean_Weather",
                    color="Clean_Weather",
                    orientation="h",
                    color_discrete_map={
                        "Clear": "#00d2ff",
                        "Cloudy": "#9e9e9e",
                        "Rainy": "#dc3545",
                    },
                    template="plotly_dark",
                    points="all",
                )
                fig_speed.update_layout(
                    showlegend=False,
                    height=350,
                    margin=dict(l=0, r=0, t=10, b=0),
                    xaxis_title="Speed (km/h)",
                    yaxis_title="",
                )
                fig_speed.update_traces(marker=dict(opacity=0.3))
                st.plotly_chart(fig_speed, use_container_width=True)

            with col_pie:
                st.markdown("**Historical Status Distribution**")
                fig_pie = px.pie(
                    hist_df,
                    names="status",
                    hole=0.6,
                    color_discrete_map={
                        "Smooth": "#28a745",
                        "Moderate": "#ffc107",
                        "Heavy Jam": "#dc3545",
                    },
                    template="plotly_dark",
                )
                fig_pie.update_layout(
                    height=350, margin=dict(l=0, r=0, t=10, b=0), showlegend=False
                )
                fig_pie.update_traces(textposition="inside", textinfo="percent+label")
                st.plotly_chart(fig_pie, use_container_width=True)

        # --- 7. Admin View ---
        st.write("")
        with st.expander(
            ":material/admin_panel_settings: System Admin: Pipeline Health Monitor",
            expanded=False,
        ):
            df_health = hist_df.copy()
            time_diffs = df_health["timestamp"].diff()
            median_interval = time_diffs.median()

            total_duration = df_health["timestamp"].max() - df_health["timestamp"].min()
            expected_runs = (
                (
                    int(
                        total_duration.total_seconds() / median_interval.total_seconds()
                    )
                    + 1
                )
                if pd.notna(median_interval) and median_interval.total_seconds() > 0
                else len(df_health)
            )
            actual_runs = len(df_health)
            uptime_pct = (
                min((actual_runs / expected_runs) * 100, 100.0)
                if expected_runs > 0
                else 100.0
            )

            total_nulls = (
                df_health["weather"].isnull().sum()
                + df_health["delay_mins"].isnull().sum()
            )

            c1, c2, c3 = st.columns(3)
            c1.metric(
                "Database Size (This Route)",
                f"{actual_runs} Rows",
                (
                    f"Sync: Every {int(median_interval.total_seconds() / 60)} mins"
                    if pd.notna(median_interval)
                    else "Gathering..."
                ),
            )
            c2.metric(
                "Scraper Uptime",
                f"{uptime_pct:.1f}%",
                "Healthy" if uptime_pct >= 90 else "- Missing Runs",
                delta_color="normal" if uptime_pct >= 90 else "inverse",
            )
            c3.metric(
                "Data Corruption",
                f"{total_nulls} Errors",
                "Clean" if total_nulls == 0 else "- Requires Cleaning",
                delta_color="normal" if total_nulls == 0 else "inverse",
            )

    else:
        st.info(
            "Collecting telemetry data... check back after the next automated chron job.",
            icon=":material/hourglass_empty:",
        )
