import gymnasium as gym
from gymnasium import spaces
import numpy as np

class TrafficEnv(gym.Env):
    """
    Custom Environment that follows gym interface.
    Simulates a 4-way intersection (e.g., Kilwa Road & Nelson Mandela Road).
    """
    metadata = {"render_modes": ["human"]}

    def __init__(self, weather="Clear"):
        super(TrafficEnv, self).__init__()
        # weather parameter allows injecting the "Speed Ceiling" effect
        self.weather = weather
        
        # Action space: 0 = Keep N/S Green, 1 = Keep E/W Green
        self.action_space = spaces.Discrete(2)
        
        # Observation space: array of 2 integers representing queue lengths [N/S_queue, E/W_queue]
        # Max queue length is capped at 100 for simplicity
        self.observation_space = spaces.Box(low=0, high=100, shape=(2,), dtype=np.int32)
        
        # Initialize queues
        self.ns_queue = 0
        self.ew_queue = 0
        self.current_light = 0 # 0 for N/S, 1 for E/W
        self.timestep = 0
        self.max_timesteps = 200

    def step(self, action):
        self.timestep += 1
        
        # Base arrival rates (cars per timestep)
        ns_arrival_rate = 2
        ew_arrival_rate = 1
        
        # SPEED CEILING EFFECT: If it's raining, more cars queue up due to slower moving traffic and caution
        if self.weather == "Rain":
            ns_arrival_rate += 3
            ew_arrival_rate += 2
            
        # Add arriving cars to queues (with some randomness)
        self.ns_queue += np.random.poisson(ns_arrival_rate)
        self.ew_queue += np.random.poisson(ew_arrival_rate)
        
        # Process the green light
        # A green light clears a fixed number of cars per timestep
        clear_rate = 5
        
        # Small penalty for switching lights (yellow light transition time)
        switch_penalty = 0
        if action != self.current_light:
            switch_penalty = 5  # Cost of 5 "cars waiting" equivalent for the delay
            self.current_light = action
            clear_rate = 2 # Slower clear rate on the turn it switches due to yellow/red overlap
            
        if self.current_light == 0:
            self.ns_queue = max(0, self.ns_queue - clear_rate)
        else:
            self.ew_queue = max(0, self.ew_queue - clear_rate)
            
        # Cap at max observation space
        self.ns_queue = min(100, self.ns_queue)
        self.ew_queue = min(100, self.ew_queue)
        
        total_waiting = self.ns_queue + self.ew_queue
        # To prevent the AI from "starving" one lane (letting it grow to 90 cars just to keep the other at 0),
        # we penalize the SQUARE of the queue lengths. A queue of [10, 0] = penalty of 100. A queue of [5, 5] = penalty of 50.
        # This forces the AI to balance the queues!
        reward = -((self.ns_queue ** 2) + (self.ew_queue ** 2) + switch_penalty)
        
        # Check if episode is done
        terminated = self.timestep >= self.max_timesteps
        truncated = False
        
        observation = np.array([self.ns_queue, self.ew_queue], dtype=np.int32)
        info = {"weather": self.weather, "total_waiting": total_waiting}
        
        return observation, reward, terminated, truncated, info

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.ns_queue = np.random.randint(0, 10)
        self.ew_queue = np.random.randint(0, 10)
        self.current_light = 0
        self.timestep = 0
        
        observation = np.array([self.ns_queue, self.ew_queue], dtype=np.int32)
        info = {}
        return observation, info
