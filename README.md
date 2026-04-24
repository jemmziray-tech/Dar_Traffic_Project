# 🚦 Dar es Salaam Smart City: Traffic & Weather Engine
![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/jemmziray-tech/Dar_Traffic_Project/traffic_scraper.yml?branch=main&style=for-the-badge&logo=githubactions&logoColor=white&label=Scraper%20Status)
![Firebase](https://img.shields.io/badge/Database-Firebase%20Firestore-FFCA28?style=for-the-badge&logo=firebase&logoColor=black)
![Python](https://img.shields.io/badge/Engine-Python%203.10-3776AB?style=for-the-badge&logo=python&logoColor=white)

## 📌 Project Overview
An automated, cloud-native **Data Engineering Pipeline** that monitors real-time traffic congestion and meteorological conditions across major arterial corridors in **Dar es Salaam, Tanzania**. 

By synchronizing high-resolution time-series data from Google Maps and Weather APIs into a NoSQL Cloud Database, this project builds a "Digital Twin" of the city's mobility patterns, enabling predictive analysis of urban bottlenecks.

---

## 🛰️ Live Architecture Flow
> *The system wakes up every 15 minutes, processes data in the cloud, and updates the global database.*

1.  **Trigger:** GitHub Actions (Cron Schedule) wakes up a headless Ubuntu server.
2.  **Ingestion:** Python engine queries **Google Maps Distance Matrix API** & **Open-Meteo API**.
3.  **Processing:** Script calculates speed differentials, congestion severity, and normalizes timestamps.
4.  **Storage:** Live data is pushed to **Google Cloud Firestore (Firebase)** for real-time app availability.
5.  **Analytics:** Historical snapshots are preserved for future Machine Learning training.

---

## ✨ Key Intelligence Features
* **🤖 100% Autonomous:** Zero-infrastructure required. Runs 24/7 via GitHub Actions.
* **🛣️ Multi-Node Monitoring:** Tracking critical bottlenecks including **Ubungo (Morogoro Rd)**, **Mwenge (Bagamoyo Rd)**, and **Tazara (Nyerere Rd)**.
* **🌧️ Weather Correlation:** Cross-references traffic delays with precipitation and temperature to quantify the "Rain Effect" on Dar commute times.
* **📊 Severity Logic:** Custom algorithms assign traffic status: `Smooth`, `Moderate`, or `Heavy Jam`.

---

## 🛠️ Tech Stack & Tools
<p align="left">
  <img src="https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54" />
  <img src="https://img.shields.io/badge/Firebase-039BE5?style=for-the-badge&logo=Firebase&logoColor=white" />
  <img src="https://img.shields.io/badge/Google_Cloud-4285F4?style=for-the-badge&logo=google-cloud&logoColor=white" />
  <img src="https://img.shields.io/badge/github%20actions-%232671E5.svg?style=for-the-badge&logo=githubactions&logoColor=white" />
</p>

---

## 🗄️ Data Schema (NoSQL)
| Data Point | Key Description | Type |
| :--- | :--- | :--- |
| `road_id` | Unique identifier for the city segment | String |
| `delay_mins` | Minutes lost relative to free-flow traffic | Integer |
| `avg_speed_kmh` | Real-time velocity of the traffic flow | Float |
| `weather_desc` | Current conditions (Temp / Rain / Sky) | String |
| `sync_time` | ISO-8601 Timestamp of cloud sync | Timestamp |

---

## 🚀 The ML Roadmap
- [x] **Phase 1:** Migrate from flat CSVs to Cloud NoSQL (Firebase).
- [ ] **Phase 2:** Build a **Streamlit Dashboard** for live city-wide visualization.
- [ ] **Phase 3:** Train an **LSTM Neural Network** to predict traffic 60 minutes in advance based on current rain intensity.

---

<p align="center">
  <b>Built with Love for the Tanzania Developer Community</b><br>
  <i>Data Engineering Portfolio by John Mziray</i>
</p>
