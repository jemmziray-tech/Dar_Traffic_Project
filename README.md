# 🚦 Dar es Salaam Live Traffic Scraper

## 📌 Project Overview
This project is an automated Data Engineering pipeline designed to collect live traffic data in Dar es Salaam, Tanzania. Specifically, it tracks the travel time on Morogoro Road from the **Ubungo Interchange to Posta (Askari Monument)**. 

Instead of relying on static reports, this scraper builds a proprietary, minute-by-minute longitudinal dataset to analyze traffic patterns, pinpoint exact *foleni* (traffic jam) peaks, and eventually train predictive machine learning models.

## 🛠️ Tech Stack & Architecture
* **Language:** Python 3.10
* **Data Source:** TomTom Routing API
* **Automation (CI/CD):** GitHub Actions
* **Storage:** CSV (Time-series data)

## ⚙️ How It Works
1. A **GitHub Actions Cron Job** is scheduled to wake up every 15 minutes, 24/7.
2. It spins up a temporary Ubuntu cloud server and runs `scrape_traffic.py`.
3. The script pings the TomTom API securely using encrypted GitHub Secrets.
4. It calculates the live traffic delay and appends a new row to `dar_morogoro_rd_traffic.csv`.
5. The robot automatically commits and pushes the updated dataset back to this repository. **Zero manual intervention required.**

## 📊 Data Dictionary
The `dar_morogoro_rd_traffic.csv` file updates automatically. Here is what the data represents:

| Column | Description |
| :--- | :--- |
| `Timestamp` | The exact Date and Time (EAT) the data was pulled. |
| `Normal_Time_Mins` | The baseline travel time (in minutes) if the road is completely empty. |
| `Live_Time_Mins` | The actual estimated travel time right now, factoring in current traffic. |
| `Delay_Mins` | The time wasted in traffic (`Live_Time` - `Normal_Time`). |

## 🚀 Future Roadmap
* [ ] Collect 30+ days of continuous data.
* [ ] Perform Exploratory Data Analysis (EDA) using `Pandas` and `Matplotlib`.
* [ ] Build a dashboard visualizing the worst times to travel on Morogoro Road.
