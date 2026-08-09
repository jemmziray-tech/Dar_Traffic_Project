// Base URL for the FastAPI backend
const API_URL = 'http://127.0.0.1:8000';

// Mapping Routes to segment arrays exactly like the backend config
const ROUTE_MAP = {
  'Morogoro Rd (Ubungo -> Posta)': ['moro_1', 'moro_2', 'moro_3', 'moro_4'],
  'Ali Hassan Mwinyi (Mwenge -> Posta)': ['ahm_1', 'ahm_2', 'ahm_3', 'ahm_4'],
  'Bagamoyo Rd (Tegeta -> Mwenge)': ['bag_1', 'bag_2', 'bag_3']
};

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const predictBtn = document.getElementById('predictBtn');
  const simulateBtn = document.getElementById('simulateBtn');
  
  // Predict Event Listener
  predictBtn.addEventListener('click', async () => {
    const routeName = document.getElementById('routeSelect').value;
    const targetTime = document.getElementById('timeInput').value;
    const targetWeather = document.getElementById('weatherSelect').value;
    
    // Default to today
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const targetDay = days[new Date().getDay()];
    const roadIds = ROUTE_MAP[routeName];

    const resultBox = document.getElementById('predictionResult');
    const delayValue = document.getElementById('delayValue');
    const delayStatus = document.getElementById('delayStatus');

    // UI Loading state
    resultBox.classList.remove('hidden');
    delayValue.textContent = 'Calculating...';
    delayStatus.textContent = 'Fetching inference';
    delayStatus.className = 'status-badge';

    try {
      const response = await fetch(`${API_URL}/predict/speed_ceiling`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          road_ids: roadIds,
          target_day: targetDay,
          target_time: targetTime,
          target_weather: targetWeather
        })
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.statusText}`);
      }

      const data = await response.json();
      
      // Update UI
      delayValue.textContent = `${data.total_delay_minutes} Mins`;
      delayStatus.textContent = data.status;
      
      if (data.status === 'Smooth Flow') {
        delayStatus.classList.add('smooth');
      } else if (data.status === 'Moderate Congestion') {
        delayStatus.classList.add('moderate');
      } else {
        delayStatus.classList.add('jammed');
      }
    } catch (err) {
      console.error(err);
      delayValue.textContent = 'Error';
      delayStatus.textContent = 'Backend Offline';
    }
  });

  // RL Simulate Event Listener
  simulateBtn.addEventListener('click', async () => {
    const nsQueue = parseInt(document.getElementById('nsQueue').value) || 0;
    const ewQueue = parseInt(document.getElementById('ewQueue').value) || 0;
    
    const rlResult = document.getElementById('rlResult');
    const actionValue = document.getElementById('actionValue');
    const lightSignal = document.getElementById('lightSignal');

    // Show box
    rlResult.classList.remove('hidden');
    actionValue.textContent = 'Simulating...';
    lightSignal.classList.remove('green');

    try {
      const response = await fetch(`${API_URL}/rl/simulate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ns_queue: nsQueue,
          ew_queue: ewQueue
        })
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.statusText}`);
      }

      const data = await response.json();
      
      actionValue.textContent = data.optimal_action_str.replace('_', ' ');
      lightSignal.classList.add('green');
      
    } catch (err) {
      console.error(err);
      actionValue.textContent = 'Agent Offline';
    }
  });
});
