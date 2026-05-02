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


@st.cache_data(ttl=60)  # Updates every 1 minute
def get_live_city_data():
    # Fetch the latest snapshot for ALL roads from the live_traffic collection
    docs = db.collection("live_traffic").stream()
    data = []
    for doc in docs:
        doc_data = doc.to_dict()
        doc_data["road_id"] = doc.id
        data.append(doc_data)
    return pd.DataFrame(data)


# Dictionary of GPS Coordinates
ROAD_COORDS = {
    "ubungo": {"lat": -6.7844, "lon": 39.2131},
    "sam_nujoma": {"lat": -6.7797, "lon": 39.2272},
    "kariakoo": {"lat": -6.8200, "lon": 39.2736},
    "uhuru_street": {"lat": -6.8183, "lon": 39.2683},
    "kilwa_mbagala": {"lat": -6.8781, "lon": 39.2711},
}


# --- 4. Main UI ---
st.title("📈 Historical Traffic Intelligence")

# --- 9. NEW: Global City-Wide Map ---
st.markdown("### 🗺️ Live City-Wide Traffic Map")

city_df = get_live_city_data()

if not city_df.empty:
    # 1. Map the GPS coordinates to the dataframe based on the road_id
    city_df["lat"] = city_df["road_id"].map(
        lambda x: ROAD_COORDS.get(x, {}).get("lat", -6.8200)
    )
    city_df["lon"] = city_df["road_id"].map(
        lambda x: ROAD_COORDS.get(x, {}).get("lon", 39.2736)
    )

    # 2. Clean up the road names for the tooltip (e.g., "sam_nujoma" -> "Sam Nujoma")
    city_df["Road Name"] = city_df["road_id"].str.replace("_", " ").str.title()

    # 3. Handle base cases where delay is 0 so the dot doesn't disappear completely
    city_df["dot_size"] = city_df["delay_mins"].apply(lambda x: x if x > 0 else 0.5)

    # 4. Draw the interactive Mapbox
    fig_map = px.scatter_mapbox(
        city_df,
        lat="lat",
        lon="lon",
        color="delay_mins",
        size="dot_size",
        size_max=20,
        hover_name="Road Name",
        hover_data={
            "status": True,
            "speed_kmh": True,
            "delay_mins": True,
            "lat": False,
            "lon": False,
            "dot_size": False,
        },
        color_continuous_scale=[
            "#28a745",
            "#ffc107",
            "#dc3545",
        ],  # Green -> Yellow -> Red
        zoom=11.5,
        mapbox_style="carto-darkmatter",
    )

    # Tighten margins so the map fills the screen beautifully
    fig_map.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

    st.plotly_chart(fig_map, use_container_width=True)
    st.markdown("---")
# --- End Global Map ---

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
        st.info("⚡ **Live Pulse Benchmark: Real-Time vs History**")
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
                color="condition_only",  # Use the clean categories for colors
                size="delay_mins",
                hover_name="weather",  # Keep the exact temp in the hover tooltip!
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

        # Extract the Hour and the Day of the Week
        df_heat["Hour"] = df_heat["timestamp"].dt.hour
        df_heat["Day"] = df_heat["timestamp"].dt.day_name()

        # Filter out the sleeping hours (Keep only 5 AM to 10 PM)
        df_heat = df_heat[(df_heat["Hour"] >= 5) & (df_heat["Hour"] <= 22)]

        # Define the correct calendar order
        days_order = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        # Group the data: Calculate the average delay
        heatmap_data = (
            df_heat.groupby(["Day", "Hour"])["delay_mins"].mean().reset_index()
        )

        # --- AI Traffic Reporter: Automated Insights ---
        if not heatmap_data.empty:
            # 1. Find the exact row with the highest average delay
            worst_idx = heatmap_data["delay_mins"].idxmax()
            worst_row = heatmap_data.loc[worst_idx]
            worst_day = worst_row["Day"]
            worst_hour_str = f"{int(worst_row['Hour']):02d}:00"
            worst_delay = worst_row["delay_mins"]

            # 2. Find the exact row with the lowest average delay
            best_idx = heatmap_data["delay_mins"].idxmin()
            best_row = heatmap_data.loc[best_idx]
            best_day = best_row["Day"]
            best_hour_str = f"{int(best_row['Hour']):02d}:00"
            best_delay = best_row["delay_mins"]

            # 3. Render the Professional Insight UI
            st.subheader(":material/analytics: Automated Insights")

            # Using st.warning for peak congestion (gives a professional yellow/red tint)
            st.warning(
                f"**Peak Congestion Detected:** Based on historical aggregates, the most severe traffic typically occurs on "
                f"**{worst_day}s at {worst_hour_str}**, with an average delay of **{worst_delay:.1f} minutes**.",
                icon=":material/warning:",
            )

            # Using st.success for smooth transit (gives a professional green tint)
            st.success(
                f"**Optimal Transit Window:** For the smoothest commute, historical data suggests traveling on "
                f"**{best_day}s around {best_hour_str}**. Average delays drop to **{best_delay:.1f} minutes**.",
                icon=":material/check_circle:",
            )
            st.markdown("---")
        # --- End of Insights Engine ---

        st.subheader("🗓️ Historical Congestion Heatmap")
        st.caption(
            "Identify the exact hours and days with the worst traffic jams. (Data recorded between 05:00 and 22:00)"
        )

        # Pivot the table to create the grid
        pivot_data = heatmap_data.pivot(
            index="Day", columns="Hour", values="delay_mins"
        ).reindex(days_order)

        # Ensure all our active hours (5 to 22) exist as columns, even if no data was captured yet
        active_hours = list(range(5, 23))
        pivot_data = pivot_data.reindex(columns=active_hours)

        # Fill empty cells with 0 so the chart draws cleanly
        pivot_data = pivot_data.fillna(0)

        # Format the column headers to look like real times (e.g., '07:00' instead of '7')
        formatted_hours = [f"{h:02d}:00" for h in pivot_data.columns]

        # Build the Plotly Heatmap
        fig_heatmap = px.imshow(
            pivot_data,
            labels=dict(x="Time of Day", y="Day of Week", color="Avg Delay (Mins)"),
            x=formatted_hours,
            y=pivot_data.index,
            color_continuous_scale="YlOrRd",
            aspect="auto",
            template="plotly_dark",
            height=500,  # Forces the chart to be taller so squares aren't squished
        )

        # --- Mobile UI Enhancements ---
        fig_heatmap.update_layout(
            margin=dict(
                l=10, r=10, t=40, b=80
            ),  # Increased bottom margin to make room for legend
            coloraxis_colorbar=dict(
                title="Avg Delay",
                orientation="h",  # Makes the legend horizontal
                y=-0.5,  # Pushes it below the x-axis text
            ),
        )

        fig_heatmap.update_xaxes(
            side="bottom",
            tickangle=-45,  # Tilts the text diagonally so it is easy to read
            tickmode="auto",
            nticks=10,  # Tells Plotly to skip some labels if the screen is too small
        )

        # Display it in Streamlit
        st.plotly_chart(fig_heatmap, use_container_width=True)

        # --- 6. The Future Forecaster (Predictive Analytics) ---
        st.markdown("---")
        st.subheader("🔮 12-Hour Traffic Forecast")
        st.caption(
            "Predicting upcoming congestion based on historical patterns. Accuracy improves as more data is collected."
        )

        if not heatmap_data.empty:
            # 1. Get the current time locally
            now = pd.Timestamp.now(tz="Africa/Dar_es_Salaam")

            # 2. Generate a list of the next 12 hours
            future_times = [now + pd.Timedelta(hours=i) for i in range(13)]

            # 3. Create a dataframe to hold our future timeline
            future_df = pd.DataFrame(
                {
                    "timestamp": future_times,
                    "Day": [t.day_name() for t in future_times],
                    "Hour": [t.hour for t in future_times],
                }
            )

            # 4. Merge our future timeline with our historical 'knowledge base' (heatmap_data)
            forecast_df = pd.merge(
                future_df, heatmap_data, on=["Day", "Hour"], how="left"
            )

            # 5. Clean up the data: Fill hours with no data (like 11 PM to 5 AM) with 0 delay
            forecast_df["delay_mins"] = forecast_df["delay_mins"].fillna(0)

            # Create a clean label for the X-axis (e.g., 'Today 14:00' or 'Tomorrow 02:00')
            def format_forecast_time(t):
                day_label = "Today" if t.date() == now.date() else "Tomorrow"
                return f"{day_label} {t.strftime('%H:00')}"

            forecast_df["time_label"] = forecast_df["timestamp"].apply(
                format_forecast_time
            )

            # 6. Build the Predictive Line Chart
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

            # Make the line look cool and futuristic (cyan color, filled area)
            fig_forecast.update_traces(line_color="#00d2ff", fill="tozeroy")

            # Display it in Streamlit
            st.plotly_chart(fig_forecast, use_container_width=True)

        # --- 7. Data Pipeline Health Monitor (Admin View) ---
        st.markdown("---")

        # We use an expander so it doesn't clutter the main user dashboard
        with st.expander("⚙️ System Admin: Pipeline Health Monitor", expanded=False):
            st.caption(
                "Real-time diagnostics of your GitHub Actions scraper and Firebase database integrity."
            )

            if not hist_df.empty:
                # 1. Sort the dataframe by time just to be safe
                df_health = hist_df.sort_values("timestamp")

                # 2. Calculate the typical time between scraper runs
                # .diff() finds the difference between consecutive rows
                time_diffs = df_health["timestamp"].diff()
                median_interval = time_diffs.median()

                # 3. Calculate Uptime (Expected vs Actual Data Points)
                # How long has the scraper been running in total?
                total_duration = (
                    df_health["timestamp"].max() - df_health["timestamp"].min()
                )

                # Prevent division by zero if there's only one row of data
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

                # Calculate the percentage (capped at 100%)
                uptime_pct = (
                    min((actual_runs / expected_runs) * 100, 100.0)
                    if expected_runs > 0
                    else 100.0
                )

                # 4. Check for Data Corruption (Null values)
                null_weather = df_health["weather"].isnull().sum()
                null_delay = df_health["delay_mins"].isnull().sum()
                total_nulls = null_weather + null_delay

                # 5. Build the UI Layout
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
                    # Show green if high uptime, red if dropping
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
