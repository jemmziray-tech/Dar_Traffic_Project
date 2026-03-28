# 🚦 Dar es Salaam Traffic & Weather Intelligence Tracker

![Data Auto-Scraper](https://github.com/jemmziray-tech/Dar_Traffic_Project/actions/workflows/traffic_scraper.yml/badge.svg)

## 📌 Project Overview
An automated, cloud-based data engineering pipeline that monitors real-time traffic congestion and weather conditions on major arterial roads in Dar es Salaam, Tanzania. 

This project creates a "Digital Twin" of the city's transport infrastructure, collecting high-resolution time-series data to measure the exact impact of rush hour, weather events, and daily commute patterns.

## ✨ Key Features
* **100% Cloud Automated:** Runs autonomously 24/7 using GitHub Actions. No local server required.
* **Multi-Node Monitoring:** Currently tracking multiple key corridors (Morogoro Road and Bagamoyo Road).
* **Weather Integration:** Cross-references traffic delays with live meteorological data to analyze the impact of rain on urban mobility.
* **Smart Categorization:** Automatically calculates average speed (km/h) and assigns severity labels to traffic jams.

## 🗄️ Data Architecture & Schema
The data is pulled via API, processed in Python, and stored in continuously updating CSV files.

| Column | Description | Data Type |
| :--- | :--- | :--- |
| `Timestamp` | Local time of data collection (UTC / EAT) | Datetime |
| `Normal_Time_Mins` | Baseline travel time with zero traffic (Free-flow) | Integer |
| `Live_Time_Mins` | Current estimated travel time | Integer |
| `Delay_Mins` | Time lost due to congestion | Integer |
| `Avg_Speed_kmh` | Calculated live speed of vehicles on the route | Float |
| `Status` | Categorical severity (Smooth, Moderate, Heavy Jam) | String |
| `Weather` | Current temperature and conditions (e.g., "26.0°C, Clear") | String |

## 🛠️ Tech Stack
* **Language:** Python 3.10
* **APIs:** TomTom Routing API (Traffic/Telematics), Open-Meteo API (Weather)
* **Automation:** GitHub Actions (Cron Jobs)
* **Storage:** CSV (Time-Series Database)

## 🚀 Future Roadmap
- [ ] Build a Python Pandas/Matplotlib script to visualize the "Monday Morning Peak".
- [ ] Add more arterial roads (e.g., Ali Hassan Mwinyi Rd, Nyerere Rd).
- [ ] Train a basic Machine Learning model to predict future delays based on historical weather.

---
*Built by [Your Name/Username] - Data Engineering Portfolio Project*
