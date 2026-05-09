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
        .limit(
            20000
        )  # THE FIX: Increased from 200 so you get weeks of data, not just 2 days!
    )
    results = query.stream()
    return pd.DataFrame([doc.to_dict() for doc in results])


# --- 4. Main UI ---
st.title(":material/monitoring: Historical Traffic Intelligence")

st.sidebar.header("Analysis Filters")


# THE FIX: Format the road names to look beautiful in the UI
def format_road_name(r_id):
    return str(r_id).replace("_", " ").title()


roads = get_roads_list()
selected_road = st.sidebar.selectbox(
    "Choose a road to analyze", roads, format_func=format_road_name
)

if selected_road:
    hist_df = get_historical_data(selected_road)
    if not hist_df.empty:
        # Convert timestamp to a Datetime object
        hist_df["timestamp"] = pd.to_datetime(hist_df["timestamp"])

        # TIMEZONE FIX: Convert from UTC to East Africa Time (Tanzania)
        hist_df["timestamp"] = hist_df["timestamp"].dt.tz_convert(
            "Africa/Dar_es_Salaam"
        )

        # Using the clean formatted name for the header
        st.subheader(f"Delay History: {format_road_name(selected_road)}")

        # --- 8. The Live Pulse Benchmark ---
        # 1. Grab the absolute newest row of data
        latest_record = hist_df.sort_values("timestamp", ascending=False).iloc[0]

        current_delay = latest_record["delay_mins"]
        current_time = latest_record["timestamp"]
        current_day = current_time.day_name()
        current_hour = current_time.hour
        current_status = latest_record["status"]

        # 2. Calculate the historical average for this exact day and hour
        historical_matches = hist_df[
            (hist_df["timestamp"].dt.day_name() == current_day)
            & (hist_df["timestamp"].dt.hour == current_hour)
        ]

        if not historical_matches.empty:
            historical_avg = historical_matches["delay_mins"].mean()
        else:
            historical_avg = current_delay  # Fallback if no history exists yet

        # 3. Calculate how much better or worse it is right now
        delay_delta = current_delay - historical_avg

        # Dynamic color fix: Grey arrow if difference is exactly 0
        pulse_color = "off" if delay_delta == 0 else "inverse"

        # 4. Display the Live Pulse Metric
        st.info(
            "**Live Pulse Benchmark: Real-Time vs History**", icon=":material/speed:"
        )
        st.metric(
            label=f"Current Status: {current_status} (Last updated at {current_time.strftime('%H:%M')})",
            value=f"{current_delay:.1f} Mins",
            delta=f"{delay_delta:.1f} mins compared to the {current_day} {current_hour:02d}:00 average",
            delta_color=pulse_color,
        )
        st.markdown("---")
        # --- End of Live Pulse ---

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

            # --- Extract just the condition (Clear, Rainy, Cloudy) for the colors ---
            hist_df["condition_only"] = hist_df["weather"].apply(
                lambda x: x.split(", ")[1] if ", " in x else x
            )

            fig_speed = px.scatter(
                hist_df,
                x="timestamp",
                y="speed_kmh",
                color="condition_only",
                size="delay_mins",
                hover_name="weather",
                color_discrete_map={
                    "Clear": "#00d2ff",  # Bright blue for clear
                    "Cloudy": "#9e9e9e",  # Grey for clouds
                    "Rainy": "#0047b3",  # Deep blue/purple for rain
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

        # --- 5. Enterprise Congestion Heatmap & Insights ---
        st.markdown("---")

        # Prepare the Data for both Insights and Heatmap
        df_heat = hist_df.copy()
        df_heat["Hour"] = df_heat["timestamp"].dt.hour
        df_heat["Day"] = df_heat["timestamp"].dt.day_name()

        # UPDATED: Filter strictly between 06:00 and 23:00
        df_heat = df_heat[(df_heat["Hour"] >= 6) & (df_heat["Hour"] <= 23)]

        days_order = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        heatmap_data = (
            df_heat.groupby(["Day", "Hour"])["delay_mins"].mean().reset_index()
        )

        # --- AI Traffic Reporter: Automated Insights ---
        if not heatmap_data.empty:
            st.subheader(":material/analytics: Automated Insights")

            # Create two side-by-side columns for our insights
            col_insight1, col_insight2 = st.columns(2)

            with col_insight1:
                st.error(
                    "**Peak Congestion (Top 3 to Avoid):**", icon=":material/warning:"
                )

                # Sort the dataframe to find the absolute highest average delays
                worst_times = heatmap_data.sort_values(
                    by="delay_mins", ascending=False
                ).head(3)

                # Loop through the top 3 and print them out
                for _, row in worst_times.iterrows():
                    st.write(
                        f"- **{row['Day']}s at {int(row['Hour']):02d}:00** ({row['delay_mins']:.1f} mins)"
                    )

            with col_insight2:
                st.success(
                    "**Optimal Transit (Top 3 to Go):**", icon=":material/check_circle:"
                )

                # Filter out zeroes (in case some hours haven't been scraped yet)
                valid_data = heatmap_data[heatmap_data["delay_mins"] > 0]

                if not valid_data.empty:
                    # Sort to find the absolute lowest average delays
                    best_times = valid_data.sort_values(
                        by="delay_mins", ascending=True
                    ).head(3)

                    # Loop through the bottom 3 and print them out
                    for _, row in best_times.iterrows():
                        st.write(
                            f"- **{row['Day']}s at {int(row['Hour']):02d}:00** ({row['delay_mins']:.1f} mins)"
                        )
                else:
                    st.write("Collecting more data to find optimal times...")

            st.markdown("---")
        # --- End of Insights Engine ---

        st.subheader(":material/calendar_month: Historical Congestion Heatmap")
        st.caption(
            "Identify the exact hours and days with the worst traffic jams. (Data recorded between 06:00 and 23:00)"
        )

        pivot_data = heatmap_data.pivot(
            index="Day", columns="Hour", values="delay_mins"
        ).reindex(days_order)

        # UPDATED: Force the columns (hours) to be exactly 6 through 23 and fill missing with 0
        active_hours = list(range(6, 24))
        pivot_data = pivot_data.reindex(columns=active_hours).fillna(0)
        formatted_hours = [f"{h:02d}:00" for h in pivot_data.columns]

        # UPDATED: Custom Traffic Color Scale (Green -> Yellow -> Orange -> Red)
        traffic_colors = [
            [0.0, "#28a745"],  # 0 delay = Green
            [0.3, "#ffc107"],  # Slight delay = Yellow
            [0.6, "#fd7e14"],  # Moderate delay = Orange
            [1.0, "#dc3545"],  # Heavy delay = Red
        ]

        fig_heatmap = px.imshow(
            pivot_data,
            labels=dict(x="Time of Day", y="Day of Week", color="Avg Delay (Mins)"),
            x=formatted_hours,
            y=pivot_data.index,
            color_continuous_scale=traffic_colors,
            aspect="auto",
            template="plotly_dark",
            height=500,
        )

        fig_heatmap.update_layout(
            xaxis_nticks=len(
                active_hours
            ),  # UPDATED: Forces every single hour tick to show up perfectly
            margin=dict(l=10, r=10, t=40, b=80),
            coloraxis_colorbar=dict(
                title="Avg Delay",
                orientation="h",
                y=-0.5,
            ),
        )

        fig_heatmap.update_xaxes(side="bottom", tickangle=-45, tickmode="auto")

        # UPDATED: Clean sentence tooltips
        fig_heatmap.update_traces(
            hovertemplate="<b>%{y} at %{x}</b><br>Average Delay: %{z:.1f} mins<extra></extra>"
        )

        st.plotly_chart(fig_heatmap, use_container_width=True)

        # --- NEW: Time-Shift Commute Optimizer ---
        st.markdown("---")
        st.subheader(":material/update: Time-Shift Commute Optimizer")
        st.caption(
            "Select your planned departure time to see if leaving slightly earlier or later saves you from traffic."
        )

        if not heatmap_data.empty:
            col_opt1, col_opt2 = st.columns(2)

            with col_opt1:
                target_day = st.selectbox("Select Travel Day", days_order)

            with col_opt2:
                # UPDATED: Matches the new 6 to 23 schedule
                available_hours = [f"{h:02d}:00" for h in range(6, 24)]
                target_hour_str = st.selectbox(
                    "Planned Departure Time", available_hours, index=2
                )
                target_hour_int = int(target_hour_str.split(":")[0])

            day_data = heatmap_data[heatmap_data["Day"] == target_day]

            if not day_data.empty:
                planned_delay_series = day_data[day_data["Hour"] == target_hour_int][
                    "delay_mins"
                ]
                planned_delay = (
                    planned_delay_series.values[0]
                    if not planned_delay_series.empty
                    else 0
                )

                early_delay_series = day_data[day_data["Hour"] == target_hour_int - 1][
                    "delay_mins"
                ]
                early_delay = (
                    early_delay_series.values[0] if not early_delay_series.empty else 0
                )

                late_delay_series = day_data[day_data["Hour"] == target_hour_int + 1][
                    "delay_mins"
                ]
                late_delay = (
                    late_delay_series.values[0] if not late_delay_series.empty else 0
                )

                best_alternative = None
                time_saved = 0
                alt_time_str = ""

                # UPDATED: Respects the 6 AM boundary
                if target_hour_int - 1 >= 6 and early_delay < planned_delay:
                    best_alternative = "earlier"
                    time_saved = planned_delay - early_delay
                    alt_time_str = f"{target_hour_int - 1:02d}:00"

                # UPDATED: Respects the 11 PM (23:00) boundary
                if (
                    target_hour_int + 1 <= 23
                    and late_delay < planned_delay
                    and (planned_delay - late_delay) > time_saved
                ):
                    best_alternative = "later"
                    time_saved = planned_delay - late_delay
                    alt_time_str = f"{target_hour_int + 1:02d}:00"

                st.write("")

                if best_alternative and time_saved > 0.5:
                    st.success(
                        f"**Pro Tip:** If you shift your commute to **{alt_time_str}**, you could avoid peak congestion and save **{time_saved:.1f} minutes** of sitting in traffic!",
                        icon=":material/tips_and_updates:",
                    )
                else:
                    st.info(
                        f"**Great Choice:** **{target_hour_str}** is currently one of the optimal times to travel. Adjusting your schedule by an hour won't save you any significant time.",
                        icon=":material/task_alt:",
                    )

        # --- 6. The Future Forecaster (Predictive Analytics) ---
        st.markdown("---")
        st.subheader(":material/online_prediction: 12-Hour Traffic Forecast")
        st.caption(
            "Predicting upcoming congestion based on historical patterns. Accuracy improves as more data is collected."
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
            )

            forecast_df["delay_mins"] = forecast_df["delay_mins"].fillna(0)

            def format_forecast_time(t):
                day_label = "Today" if t.date() == now.date() else "Tomorrow"
                return f"{day_label} {t.strftime('%H:00')}"

            forecast_df["time_label"] = forecast_df["timestamp"].apply(
                format_forecast_time
            )

            fig_forecast = px.line(
                forecast_df,
                x="time_label",
                y="delay_mins",
                markers=True,
                labels={
                    "time_label": "Upcoming Timeline",
                    "delay_mins": "Predicted Delay (Mins)",
                },
                template="plotly_dark",
            )

            fig_forecast.update_traces(line_color="#00d2ff", fill="tozeroy")
            st.plotly_chart(fig_forecast, use_container_width=True)

        # --- 7. Data Pipeline Health Monitor (Admin View) ---
        st.markdown("---")

        with st.expander(
            ":material/admin_panel_settings: System Admin: Pipeline Health Monitor",
            expanded=False,
        ):
            st.caption(
                "Real-time diagnostics of your GitHub Actions scraper and Firebase database integrity."
            )

            if not hist_df.empty:
                df_health = hist_df.sort_values("timestamp")
                time_diffs = df_health["timestamp"].diff()
                median_interval = time_diffs.median()

                total_duration = (
                    df_health["timestamp"].max() - df_health["timestamp"].min()
                )

                if pd.notna(median_interval) and median_interval.total_seconds() > 0:
                    expected_runs = (
                        int(
                            total_duration.total_seconds()
                            / median_interval.total_seconds()
                        )
                        + 1
                    )
                else:
                    expected_runs = len(df_health)

                actual_runs = len(df_health)

                uptime_pct = (
                    min((actual_runs / expected_runs) * 100, 100.0)
                    if expected_runs > 0
                    else 100.0
                )

                null_weather = df_health["weather"].isnull().sum()
                null_delay = df_health["delay_mins"].isnull().sum()
                total_nulls = null_weather + null_delay

                col_admin1, col_admin2, col_admin3 = st.columns(3)

                with col_admin1:
                    st.metric(
                        label="Database Size",
                        value=f"{actual_runs} Rows",
                        delta=(
                            f"Median Run: Every {int(median_interval.total_seconds() / 60)} mins"
                            if pd.notna(median_interval)
                            else "Gathering data..."
                        ),
                    )

                with col_admin2:
                    uptime_color = "normal" if uptime_pct >= 90 else "inverse"
                    st.metric(
                        label="Scraper Uptime",
                        value=f"{uptime_pct:.1f}%",
                        delta=(
                            "Healthy" if uptime_pct >= 90 else "- Missing Runs Detected"
                        ),
                        delta_color=uptime_color,
                    )

                with col_admin3:
                    st.metric(
                        label="Data Corruption (Nulls)",
                        value=f"{total_nulls} Errors",
                        delta=(
                            "Clean Database"
                            if total_nulls == 0
                            else "- Requires Cleaning"
                        ),
                        delta_color="normal" if total_nulls == 0 else "inverse",
                    )
            else:
                st.info("Not enough data to calculate pipeline health.")

    else:
        st.info("Collecting data... check back after the next scheduled run!")
