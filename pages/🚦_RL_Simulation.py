import streamlit as st
import time
import numpy as np
import pandas as pd

import sys
import os

# Add parent directory to path so we can import rl_env
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from rl_env import TrafficEnv
    from stable_baselines3 import DQN
    RL_AVAILABLE = True
except ImportError:
    RL_AVAILABLE = False

st.set_page_config(page_title="RL Traffic Simulation", page_icon="🚦", layout="wide")

# --- PREMIUM DESIGN SYSTEM CSS ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, [class*="css"], .stApp { font-family: 'Inter', sans-serif !important; background-color: #0A0F1E; color: #E8EAF0; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0D1426 0%, #0A0F1E 100%) !important; border-right: 1px solid rgba(0, 212, 255, 0.1); }
.block-container { padding-top: 1.8rem; padding-bottom: 2rem; max-width: 98%; }
div[data-testid="stMetricValue"] { font-weight: 700; font-size: 1.8rem !important; letter-spacing: -0.5px; color: #FFFFFF; }
div[data-testid="stMetricLabel"] { color: #8892A4 !important; font-size: 0.75rem; font-weight: 500; letter-spacing: 0.5px; text-transform: uppercase; }
.page-header { font-size: 1.8rem; font-weight: 800; color: #FFFFFF; letter-spacing: -0.8px; }
.page-sub { font-size: 0.85rem; color: #5C6680; margin-top: 4px; margin-bottom: 20px; }
.stat-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(0,212,255,0.12); border-radius: 10px; padding: 16px 20px; text-align: center; }
.light-green { color: #2ED573; font-weight: 800; font-size: 1.2rem; }
.light-red { color: #FF4757; font-weight: 800; font-size: 1.2rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="page-header">🚦 Autonomous RL Intersection Control</div><div class="page-sub">Live Deep Q-Network (DQN) agent dynamically adjusting traffic lights to minimize gridlock.</div>', unsafe_allow_html=True)

if not RL_AVAILABLE:
    st.error("Reinforcement Learning packages are not installed or model is missing. Please run `pip install stable-baselines3[extra] gymnasium` and then run `python train_rl.py`.")
    st.stop()

model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rl_traffic_model.zip")
if not os.path.exists(model_path):
    st.warning("⚠️ RL Model not found! Please run `python train_rl.py` first to generate the `rl_traffic_model.zip`.")
    st.stop()

# Load the trained RL model
def load_rl_model():
    return DQN.load(model_path)

model = load_rl_model()

# Simulation Controls
st.sidebar.markdown("### 🎛️ Simulation Controls")
weather = st.sidebar.radio("Environmental Condition (Speed Ceiling)", ["Clear", "Rain"])
sim_speed = st.sidebar.slider("Simulation Speed (Seconds per step)", 0.05, 1.0, 0.2)

col1, col2 = st.columns(2)
start_button = col1.button("▶️ Start Smart RL Agent")
dumb_button = col2.button("⏱️ Start Dumb Fixed Timer")

st.divider()

# Layout for the simulation
light_col, metric_col = st.columns([1, 2])

with light_col:
    st.markdown("### Current Light Status")
    ns_light_ph = st.empty()
    ew_light_ph = st.empty()

with metric_col:
    st.markdown("### Queue Lengths")
    colA, colB = st.columns(2)
    with colA:
        ns_queue_ph = st.empty()
    with colB:
        ew_queue_ph = st.empty()

chart_ph = st.empty()

def render_lights(current_light):
    if current_light == 0:
        ns_light_ph.markdown("<div class='stat-card'>North/South<br><span class='light-green'>🟢 GREEN</span></div>", unsafe_allow_html=True)
        ew_light_ph.markdown("<div class='stat-card'>East/West<br><span class='light-red'>🔴 RED</span></div>", unsafe_allow_html=True)
    else:
        ns_light_ph.markdown("<div class='stat-card'>North/South<br><span class='light-red'>🔴 RED</span></div>", unsafe_allow_html=True)
        ew_light_ph.markdown("<div class='stat-card'>East/West<br><span class='light-green'>🟢 GREEN</span></div>", unsafe_allow_html=True)

if start_button or dumb_button:
    env = TrafficEnv(weather=weather)
    obs, info = env.reset()
    
    history_ns = []
    history_ew = []
    
    fixed_timer_state = 0
    fixed_timer_count = 0
    
    for i in range(100): # Run 100 steps
        # Decide Action
        if start_button:
            # Action array returned by predict is [action], we just want the scalar
            action, _states = model.predict(obs, deterministic=True)
            action = int(action)
        else:
            # Dumb timer: switch every 5 steps
            fixed_timer_count += 1
            if fixed_timer_count > 5:
                fixed_timer_state = 1 - fixed_timer_state
                fixed_timer_count = 0
            action = fixed_timer_state
            
        # Step environment
        obs, reward, done, truncated, info = env.step(action)
        
        # Update UI
        render_lights(env.current_light)
        ns_queue_ph.metric(label="North/South Queue (Cars)", value=int(obs[0]), delta=f"Total Waiting: {info['total_waiting']}", delta_color="inverse")
        ew_queue_ph.metric(label="East/West Queue (Cars)", value=int(obs[1]))
        
        history_ns.append(int(obs[0]))
        history_ew.append(int(obs[1]))
        
        df = pd.DataFrame({
            "N/S Queue": history_ns,
            "E/W Queue": history_ew
        })
        chart_ph.line_chart(df, height=300, use_container_width=True)
        
        time.sleep(sim_speed)
        
        if done:
            break
            
    st.success("Simulation Complete!")
