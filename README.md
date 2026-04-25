# <img src="https://fonts.gstatic.com/s/e/notoemoji/latest/1f6a6/512.gif" width="35" align="center"> Dar es Salaam Smart City: Traffic & Weather Engine

![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/jemmziray-tech/Dar_Traffic_Project/traffic_scraper.yml?branch=main&style=for-the-badge&logo=githubactions&logoColor=white&label=Scraper%20Status)
![Firebase](https://img.shields.io/badge/Database-Firebase%20Firestore-FFCA28?style=for-the-badge&logo=firebase&logoColor=black)
![Python](https://img.shields.io/badge/Engine-Python%203.10-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)

### <img src="https://fonts.gstatic.com/s/e/notoemoji/latest/1f534/512.gif" width="20" align="center"> [Live Dashboard: View the Dar es Salaam Command Center Here](https://dartrafficproject-johnmziray.streamlit.app/)

## <img src="https://fonts.gstatic.com/s/e/notoemoji/latest/1f4cc/512.gif" width="28" align="center"> Project Overview

An automated, cloud-native **Data Engineering Pipeline & Intelligence Dashboard** that monitors real-time traffic congestion and meteorological conditions across major arterial corridors in **Dar es Salaam, Tanzania**.

By synchronizing high-resolution time-series data from Google Maps and Weather APIs into a NoSQL Cloud Database, this project builds a "Digital Twin" of the city's mobility patterns. The data is visualized in a live, 3D spatial dashboard, laying the foundation for predictive analysis of urban bottlenecks.

---

## <img src="https://fonts.gstatic.com/s/e/notoemoji/latest/1f4e1/512.gif" width="28" align="center"> Live Architecture Flow

> _The system wakes up autonomously, processes data in the cloud, updates the global database, and serves it to a live web application._

1.  **Trigger:** GitHub Actions (Cron Schedule) wakes up a headless server.
2.  **Ingestion:** Python engine queries **Google Maps Distance Matrix API** & **Open-Meteo API**.
3.  **Processing:** Script calculates speed differentials, congestion severity, and normalizes timestamps.
4.  **Storage:** Live data is pushed to **Google Cloud Firestore (Firebase)**.
5.  **Analytics:** Historical snapshots are preserved for future Machine Learning training.
6.  **Visualization:** **Streamlit Cloud** pulls live metrics and plots them on a 3D Pydeck geospatial map.

---

## <img src="https://fonts.gstatic.com/s/e/notoemoji/latest/2728/512.gif" width="28" align="center"> Key Intelligence Features

- <img src="https://fonts.gstatic.com/s/e/notoemoji/latest/1f916/512.gif" width="22" align="center"> **100% Autonomous Pipeline:** Zero-infrastructure required. Data ingestion runs 24/7 via GitHub Actions.
- <img src="https://fonts.gstatic.com/s/e/notoemoji/latest/1f30d/512.gif" width="22" align="center"> **3D Spatial Mapping:** Real-time city congestion heatmap using `Pydeck` and coordinate mapping.
- <img src="https://fonts.gstatic.com/s/e/notoemoji/latest/1f697/512.gif" width="22" align="center"> **Multi-Node Monitoring:** Tracking critical bottlenecks including **Ubungo (Morogoro Rd)**, **Mwenge (Bagamoyo Rd)**, and **Tazara (Nyerere Rd)**.
- <img src="https://fonts.gstatic.com/s/e/notoemoji/latest/1f327/512.gif" width="22" align="center"> **Weather Correlation:** Cross-references traffic delays with precipitation and temperature to quantify the "Rain Effect" on Dar commute times.
- <img src="https://fonts.gstatic.com/s/e/notoemoji/latest/1f510/512.gif" width="22" align="center"> **Dual-Environment Security:** Implements Streamlit Secrets for cloud deployment and secure local JSON parsing for development.

---

## <img src="https://fonts.gstatic.com/s/e/notoemoji/latest/1f6e0/512.gif" width="28" align="center"> Tech Stack & Tools

<p align="left">
  <img src="https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54" />
  <img src="https://img.shields.io/badge/Firebase-039BE5?style=for-the-badge&logo=Firebase&logoColor=white" />
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white" />
  <img src="https://img.shields.io/badge/Plotly-239120?style=for-the-badge&logo=plotly&logoColor=white" />
  <img src="https://img.shields.io/badge/Google_Cloud-4285F4?style=for-the-badge&logo=google-cloud&logoColor=white" />
  <img src="https://img.shields.io/badge/github%20actions-%232671E5.svg?style=for-the-badge&logo=githubactions&logoColor=white" />
</p>

---

## <img src="https://fonts.gstatic.com/s/e/notoemoji/latest/1f4be/512.gif" width="28" align="center"> Data Schema (NoSQL)

| Data Point      | Key Description                            | Type      |
| :-------------- | :----------------------------------------- | :-------- |
| `road_id`       | Unique identifier for the city segment     | String    |
| `delay_mins`    | Minutes lost relative to free-flow traffic | Integer   |
| `avg_speed_kmh` | Real-time velocity of the traffic flow     | Float     |
| `weather_desc`  | Current conditions (Temp / Rain / Sky)     | String    |
| `sync_time`     | ISO-8601 Timestamp of cloud sync           | Timestamp |

---

## <img src="https://fonts.gstatic.com/s/e/notoemoji/latest/1f680/512.gif" width="28" align="center"> The ML Roadmap

- [x] **Phase 1:** Migrate from flat CSVs to Cloud NoSQL (Firebase).
- [x] **Phase 2:** Build and deploy a real-time **Streamlit Dashboard** with 3D Spatial Mapping.
- [ ] **Phase 3:** Train an **LSTM Neural Network** to predict traffic 60 minutes in advance based on current rain intensity and historical delays.

---

<p align="center">
  <b>Built with Love for the Tanzania Developer Community</b><br>
  <i>Data Engineering Portfolio by John Mziray</i>
</p>
