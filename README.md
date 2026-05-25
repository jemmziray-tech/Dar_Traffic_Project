# <img src="https://fonts.gstatic.com/s/e/notoemoji/latest/1f6a6/512.gif" width="35" align="center"> Dar es Salaam Smart City Engine: AI-Powered Predictive Traffic Intelligence

![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/jemmziray-tech/Dar_Traffic_Project/traffic_scraper.yml?branch=main&style=for-the-badge&logo=githubactions&logoColor=white&label=Autonomous%20Scraper)
![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/jemmziray-tech/Dar_Traffic_Project/retrainai.yml?branch=main&style=for-the-badge&logo=githubactions&logoColor=white&label=MLOps%20Pipeline)
![Firebase](https://img.shields.io/badge/Data_Vault-Firebase%20NoSQL-FFCA28?style=for-the-badge&logo=firebase&logoColor=black)
![Google Gemini](https://img.shields.io/badge/AI_Copilot-Gemini%202.5%20Flash-4285F4?style=for-the-badge&logo=googlegemini&logoColor=white)
![Python](https://img.shields.io/badge/Engine-Python%203.10-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)

### <img src="https://fonts.gstatic.com/s/e/notoemoji/latest/1f534/512.gif" width="20" align="center"> [Live Executive Dashboard: View the Command Center Here](https://dartrafficproject-johnmziray.streamlit.app/)

## <img src="https://fonts.gstatic.com/s/e/notoemoji/latest/1f4cc/512.gif" width="28" align="center"> Executive Summary

Traffic congestion in Dar es Salaam is a critical bottleneck, costing logistics fleets thousands of Tanzanian Shillings (TZS) per minute in wasted fuel and lost operational capacity.

The **Dar es Salaam Smart City Engine** is an enterprise-grade "Digital Twin" of the city's mobility network. Unlike consumer apps that *react* to existing traffic jams, this platform uses a Scikit-Learn **Machine Learning Engine** trained on historical spatial and meteorological telemetry to **predict gridlock before it forms**. Paired with a **Gemini 2.5 Flash GenAI Copilot**, the engine translates complex mathematical variance into actionable, live routing advice for commercial fleet dispatchers and city planners.

---

## <img src="https://fonts.gstatic.com/s/e/notoemoji/latest/1f4e1/512.gif" width="28" align="center"> Enterprise Architecture

```mermaid
graph TD
    subgraph "1. Autonomous Telemetry Pipeline"
        GCS[Google Cloud Scheduler] -->|Webhook every 15m| GHA_Scraper[GitHub Actions: ThreadPool Scraper]
        GHA_Scraper -->|Concurrent I/O| GMaps[Google Maps Spatial API]
        GHA_Scraper -->|Concurrent I/O| Weather[Open-Meteo API]
    end

    subgraph "2. The Data Vault (NoSQL)"
        GMaps -->|Sanitized JSON| FB[(Google Cloud Firestore)]
        Weather -->|Sanitized JSON| FB
    end

    subgraph "3. Predictive MLOps & Spatial DNA"
        GHA_ML[GitHub Actions: Training Pipeline] -->|Historical Batch| FB
        GHA_ML -->|Random Forest Regression| Model[Scikit-Learn Model]
        GHA_ML -->|Unsupervised K-Means| Clustering[Road Behavioral Clustering]
        Model --> Repo[traffic_model.pkl]
    end

    subgraph "4. Executive Command Center"
        Streamlit[Streamlit Cloud UI] -->|Loads Model| Repo
        Streamlit -->|Infers Matrix| Gemini[Gemini 2.5 Flash Copilot]
        Gemini -->|Fleet Advisory| Streamlit
        Streamlit -->|Calculates Capital Friction| ROI[Economic Simulator]
    end

    User((Fleet Dispatcher)) -->|Optimizes Routes| Streamlit

The architecture is fully decoupled, ensuring the high-speed data ingestion environment operates entirely independent of the user-facing Machine Learning dashboard.

Orchestration: Google Cloud Scheduler triggers a precise webhook every 15 minutes to guarantee telemetry consistency.

High-Speed I/O: GitHub Actions utilizes Python's ThreadPoolExecutor for concurrent scraping across 21 major city arteries, reducing API blocking.

The Vault: Data is sanitized and pushed securely to Google Cloud Firestore (Firebase) to accommodate flexible time-series JSON documents.

Spatial DNA (Unsupervised ML): K-Means clustering mathematically groups the city into High-Velocity Corridors, Rush-Hour Traps, and Chronic Gridlock Zones.

Predictive Engine (Supervised ML): A Random Forest model is trained on historical data to predict exact minutes of delay based on time, route, and weather.

GenAI Intelligence: Google Gemini 2.5 Flash acts as an AI Fleet Copilot, converting pure mathematical output into actionable departure strategies.

 Core Intelligence Capabilities
100% Autonomous Scraper: Zero human intervention required; powered by Google Cloud triggers.

Capital Friction Simulator: Translates abstract "minutes delayed" into quantifiable financial loss (TZS) for heavy logistics fleets.

Unsupervised K-Means Clustering: AI profiles the "Spatial DNA" of roads by plotting Severity against Unpredictability (Volatility).

3D Geospatial Heatmaps: Real-time city congestion visualization engineered with Pydeck.

Conversational AI Copilot: Instant, mathematically-backed routing advice generated by Google Gemini.

 Tech Stack & Tools
 Engineering Milestones
Building this enterprise-grade pipeline required overcoming real-world engineering hurdles:

I/O Bottleneck Optimization: Refactored sequential API calls into asynchronous ThreadPoolExecutor processes to prevent server timeouts.

Separation of Concerns: Isolated dependencies into scraper_requirements.txt vs train_requirements.txt to eliminate "Dependency Hell" in CI/CD.

Decoupled Orchestration: Migrated from GitHub Cron (unreliable) to Google Cloud Scheduler for precise, guaranteed telemetry execution.

 Scaling Roadmap & Future Infrastructure
The platform is designed to scale from an advisory MVP into a fully integrated, national municipal tool.

[x] Phase 1 (Completed): Telemetry pipeline construction and MVP UI deployment.

[x] Phase 2 (Completed): Unsupervised spatial clustering and Gemini AI Copilot integration.

[ ] Phase 3 (Scaling): Transitioning data layers to PostgreSQL with TimescaleDB for enterprise time-series handling and creating a native mobile app for on-road fleet drivers.

[ ] Phase 4 (V2X Micro-Mobility): Partnering with LATRA to ingest live Vehicle-to-Everything (V2X) GPS pings directly from public transit (Daladalas) to close micro-mobility blind spots.

[ ] Phase 5 (Physical Actuation): Engineering a direct municipal "Smart City API" to allow our predictive AI to override and optimize Dar es Salaam's physical traffic light timers dynamically.
