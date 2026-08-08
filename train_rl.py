import os
import sys
import io

# Fix Windows console encoding issues
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    from stable_baselines3 import DQN
except ImportError:
    print("❌ Error: stable-baselines3 is not installed. Run: pip install stable-baselines3[extra] gymnasium")
    sys.exit(1)

from rl_env import TrafficEnv

print("🚦 Initializing Reinforcement Learning Training Environment...")

# Create the environment
env = TrafficEnv(weather="Clear")

# Initialize the Deep Q-Network (DQN) model
print("🧠 Building Deep Q-Network (DQN)...")
model = DQN(
    "MlpPolicy", 
    env, 
    learning_rate=1e-3, 
    buffer_size=50000, 
    learning_starts=1000, 
    batch_size=32, 
    gamma=0.99, 
    verbose=1
)

# Train the agent
print("⏳ Training RL Agent for 20,000 timesteps... (This may take a minute)")
model.learn(total_timesteps=20000, progress_bar=True)

# Save the trained model
model_path = "rl_traffic_model.zip"
model.save(model_path)
print(f"✅ Training complete! Model securely saved as '{model_path}'")

# Test it briefly
print("\n🧪 Running a quick 10-step simulation test...")
obs, info = env.reset()
total_reward = 0
for i in range(10):
    action, _states = model.predict(obs, deterministic=True)
    obs, reward, done, truncated, info = env.step(action)
    total_reward += reward
    action_str = 'N/S Green' if action == 0 else 'E/W Green'
    print(f"Step {i+1}: Queue [N/S: {obs[0]}, E/W: {obs[1]}] -> Action: {action_str} | Reward: {reward}")

print("✅ RL Pipeline Verified and Ready for Streamlit!")
