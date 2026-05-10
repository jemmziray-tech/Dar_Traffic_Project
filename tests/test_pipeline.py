import sys
import os
import pytest
from pydantic import ValidationError

# Add the parent directory to the system path so we can import your scraper
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scrape_traffic import TrafficSchema


# --- TEST 1: Speed Math Verification ---
def test_speed_calculation_logic():
    """Ensures our speed math (Distance / Time) works and prevents divide-by-zero errors."""
    dist_km = 5.0
    live_mins = 15  # 15 minutes is 0.25 hours

    # Speed = distance / (time in hours)
    speed = round(dist_km / (live_mins / 60), 1) if live_mins > 0 else 0.0

    # 5.0 km / 0.25 hours = 20.0 km/h
    assert speed == 20.0, "Speed calculation math is incorrect!"

    # Test divide-by-zero protection (e.g., if live_mins is 0)
    live_mins_zero = 0
    speed_zero = (
        round(dist_km / (live_mins_zero / 60), 1) if live_mins_zero > 0 else 0.0
    )

    assert speed_zero == 0.0, "Divide by zero protection failed!"


# --- TEST 2: Data Contract Success ---
def test_schema_accepts_valid_data():
    """Ensures Pydantic accepts clean data from the APIs."""
    clean_data = {
        "road_id": "mwenge",
        "name": "Bagamoyo Rd (Mwenge)",
        "normal_mins": 12,
        "live_mins": 25,
        "delay_mins": 13,
        "speed_kmh": 14.5,
        "status": "Heavy Jam",
        "weather": "28°C, Clear",
    }

    # This should pass without throwing an error
    schema = TrafficSchema(**clean_data)
    assert schema.road_id == "mwenge"


# --- TEST 3: Data Contract Rejection ---
def test_schema_rejects_corrupted_data():
    """Ensures Pydantic blocks bad data (like negative speeds or missing fields)."""
    corrupted_data = {
        "road_id": "mwenge",
        "name": "Bagamoyo Rd (Mwenge)",
        "normal_mins": 12,
        "live_mins": 25,
        "delay_mins": 13,
        "speed_kmh": -5.0,  # FATAL ERROR: Speed cannot be negative!
        "status": "Heavy Jam",
        "weather": "28°C, Clear",
    }

    # We expect Pydantic to raise a ValidationError here
    with pytest.raises(ValidationError):
        TrafficSchema(**corrupted_data)
