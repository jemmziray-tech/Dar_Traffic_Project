import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

artifact_dir = r"C:\Users\jemmz\.gemini\antigravity\brain\fbf100f3-1048-4c82-9d3e-b16b95fe5e20"
sns.set_theme(style="darkgrid")

df = pd.read_csv("historical_traffic_data.csv")
df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed', utc=True).dt.tz_convert('Africa/Dar_es_Salaam')
df['hour'] = df['timestamp'].dt.hour
df['day_name'] = df['timestamp'].dt.day_name()
def map_weather(w):
    w = str(w).lower()
    if any(r in w for r in ["rain", "drizzle", "shower", "storm"]): return "Rainy"
    elif any(c in w for c in ["cloud", "overcast"]): return "Cloudy"
    return "Clear"
df['weather_clean'] = df['weather'].apply(map_weather)

# Insight 1: Hourly delay
plt.figure(figsize=(10, 5))
sns.lineplot(data=df, x='hour', y='delay_mins', estimator='mean', errorbar=None, marker='o')
plt.title('Average Network Delay by Hour of Day')
plt.xlabel('Hour (24h)')
plt.ylabel('Average Delay (Minutes)')
plt.xticks(range(0, 24))
plt.savefig(os.path.join(artifact_dir, 'eda_hourly_delay.png'))
plt.close()

# Insight 2: Worst Corridors
road_delays = df.groupby('name')['delay_mins'].mean().sort_values(ascending=False).reset_index()
plt.figure(figsize=(10, 6))
sns.barplot(data=road_delays.head(10), x='delay_mins', y='name', palette='Reds_r')
plt.title('Top 10 Worst Arteries by Average Delay')
plt.xlabel('Average Delay (Minutes)')
plt.ylabel('')
plt.tight_layout()
plt.savefig(os.path.join(artifact_dir, 'eda_worst_corridors.png'))
plt.close()

# Insight 3: Weather Impact
plt.figure(figsize=(8, 5))
sns.boxplot(data=df, x='weather_clean', y='speed_kmh', palette=['#00D4FF', '#8892A4', '#FF4757'])
plt.title('Impact of Weather on Traffic Speed')
plt.xlabel('Condition')
plt.ylabel('Speed (km/h)')
plt.savefig(os.path.join(artifact_dir, 'eda_weather_impact.png'))
plt.close()

print("Plots generated.")
