import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime
import pytz

# --- 1. Setup Page Config ---
st.set_page_config(page_title="Dar Traffic Live", layout="wide", page_icon="🚦")

# --- 2. Connect to Firebase (Stable Multi-Page Logic) ---
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-key.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()


# --- 3. Helper Functions ---
def get_live_data():
    docs = db.collection("live_traffic").stream()
    data = []
    for doc in docs:
        row = doc.to_dict()
        row["id"] = doc.id
        data.append(row)
    return pd.DataFrame(data)


# --- 4. FETCH DATA ---
df_raw = get_live_data()

# --- 5. SIDEBAR: Control Center ---
st.sidebar.header("🕹️ Control Center")

# Local Tanzania Time
tz = pytz.timezone("Africa/Dar_es_Salaam")
now = datetime.now(tz)
st.sidebar.markdown(f"### 🕒 {now.strftime('%I:%M %p')}")

# Peak Hour Logic
hour = now.hour
if 7 <= hour <= 9:
    st.sidebar.warning("⚡ Morning Peak")
elif 16 <= hour <= 19:
    st.sidebar.error("🌙 Evening Peak")
else:
    st.sidebar.success("🟢 Off-Peak")

st.sidebar.markdown("---")

# Status Filtering
if not df_raw.empty:
    status_filter = st.sidebar.multiselect(
        "Filter Roads by Status",
        options=["Smooth", "Moderate", "Heavy Jam"],
        default=["Smooth", "Moderate", "Heavy Jam"],
    )
    df = df_raw[df_raw["status"].isin(status_filter)]
else:
    df = df_raw

# Export Data Button
if not df.empty:
    csv = df.to_csv(index=False).encode("utf-8")
    st.sidebar.download_button(
        "📥 Export Live CSV", data=csv, file_name="dar_traffic_live.csv"
    )

st.sidebar.caption("Built by John Mziray | Data Engineering Portfolio")

# --- 6. MAIN DASHBOARD ---
st.title("🚦 Dar es Salaam Smart City Traffic")
st.markdown("_Real-time mobility intelligence platform_")

if not df.empty:
    # --- HERO SECTION ---
    st.markdown("### 🌆 City-Wide Overview")
    c1, c2, c3 = st.columns(3)

    avg_speed = df_raw["speed_kmh"].mean()
    total_delay = df_raw["delay_mins"].sum()
    bottleneck_row = df_raw.loc[df_raw["delay_mins"].idxmax()]

    with c1:
        st.metric("Avg City Speed", f"{avg_speed:.1f} km/h")
    with c2:
        st.metric(
            "Total Active Delay",
            f"{total_delay} min",
            delta="Across all nodes",
            delta_color="inverse",
        )
    with c3:
        st.metric("Top Bottleneck", bottleneck_row["name"])

    # --- ADVANCED INTELLIGENCE SECTION ---
    with st.expander("🔬 Advanced System Intelligence", expanded=True):
        ai_col1, ai_col2 = st.columns([2, 1])

        with ai_col1:
            if total_delay > 60:
                st.error(
                    f"🔴 **Significant Gridlock:** Total city delay is {total_delay} minutes. High congestion detected at **{bottleneck_row['name']}**."
                )
            elif (
                "Rain" in df_raw["weather"].iloc[0]
                or "Drizzle" in df_raw["weather"].iloc[0]
            ):
                st.warning(
                    "⚠️ **Weather Advisory:** Precipitation detected. Expect traffic flow efficiency to drop."
                )
            else:
                st.success(
                    "✅ **Optimal Flow:** City traffic is moving within normal parameters."
                )

        with ai_col2:
            efficiency = 100 - min((total_delay / 150) * 100, 100)
            st.write(f"**City Flow Efficiency:** {efficiency:.1f}%")
            st.progress(efficiency / 100)

    st.markdown("---")

    # --- GRID LAYOUT ---
    num_cols = 3
    for i in range(0, len(df), num_cols):
        chunk = df.iloc[i : i + num_cols]
        cols = st.columns(num_cols)

        for index, row in chunk.reset_index().iterrows():
            with cols[index]:
                status_emoji = (
                    "🟢"
                    if row["status"] == "Smooth"
                    else "🟡" if row["status"] == "Moderate" else "🔴"
                )
                with st.container(border=True):
                    st.markdown(f"### {status_emoji} {row['name']}")
                    st.metric(
                        label="Live Velocity",
                        value=f"{row['speed_kmh']} km/h",
                        delta=f"{row['delay_mins']} min delay",
                        delta_color="inverse",
                    )
                    speed_percent = min(row["speed_kmh"] / 50.0, 1.0)
                    st.progress(speed_percent)
                    st.caption(f"☁️ {row['weather']} | 🛰️ ID: {row['id']}")
