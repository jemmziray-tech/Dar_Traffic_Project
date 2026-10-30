"""Validated observations and transparent calculations shared by all pages."""
import numpy as np
import pandas as pd
from config import ROAD_MAP

FRESH_MINUTES = 90
NUMERIC = ['live_mins', 'normal_mins', 'distance_km']
COLUMNS = ['road_id', 'name', 'timestamp', *NUMERIC, 'delay_mins', 'speed_kmh', 'weather', 'age_mins']


def observations(records, now=None):
    """Reject legacy, incomplete, future-dated and invalid measurements."""
    frame = pd.DataFrame(records)
    required = {'road_id', 'timestamp', 'schema_version', 'traffic_observed', 'source', *NUMERIC}
    if frame.empty or not required.issubset(frame.columns):
        return pd.DataFrame(columns=COLUMNS)
    frame = frame.copy()
    frame['timestamp'] = pd.to_datetime(frame['timestamp'], utc=True, errors='coerce')
    for name in NUMERIC:
        frame[name] = pd.to_numeric(frame[name], errors='coerce')
    valid = ((frame['schema_version'] == 2) & (frame['traffic_observed'] == True)
             & (frame['source'] == 'google_distance_matrix') & frame['road_id'].isin(ROAD_MAP)
             & frame['timestamp'].notna() & np.isfinite(frame[NUMERIC]).all(axis=1)
             & (frame['live_mins'] > 0) & (frame['normal_mins'] > 0) & (frame['distance_km'] > 0))
    frame = frame.loc[valid].copy()
    instant = pd.Timestamp.now(tz='UTC') if now is None else pd.Timestamp(now)
    frame['age_mins'] = (instant - frame['timestamp']).dt.total_seconds() / 60
    frame = frame[frame['age_mins'] >= 0].copy()
    computed = (frame['live_mins'] - frame['normal_mins']).clip(lower=0)
    # The collector computes delay from seconds before rounding durations. Preserve
    # that value rather than subtracting two independently rounded minute fields.
    frame['delay_mins'] = pd.to_numeric(frame.get('delay_mins', computed), errors='coerce')
    frame = frame[np.isfinite(frame['delay_mins']) & (frame['delay_mins'] >= 0)
                  & ((frame['delay_mins'] - computed).abs() <= 0.021)].copy()
    frame['speed_kmh'] = frame['distance_km'] / (frame['live_mins'] / 60)
    frame['name'] = frame['road_id'].map(ROAD_MAP)
    frame['weather'] = frame.get('weather', pd.Series('Unknown', index=frame.index)).fillna('Unknown')
    return frame[COLUMNS].drop_duplicates(['road_id', 'timestamp']).sort_values('timestamp')


def recent(frame):
    return frame[frame['age_mins'] <= FRESH_MINUTES].copy()


def latest(frame):
    return frame.sort_values('timestamp').drop_duplicates('road_id', keep='last').copy()


def scenario(travel, baseline, reduction):
    """Apply an assumed reduction only to the positive additional delay."""
    delay = max(float(travel) - float(baseline), 0)
    saved = delay * float(reduction) / 100
    return float(travel) - saved, saved


def hourly_profile(frame):
    """Summarize observed hours; never interpolate unobserved hours."""
    if frame.empty:
        return pd.DataFrame(columns=['Hour (EAT)', 'Median delay (min)', 'Observations', 'Days'])
    work = frame.copy()
    local = work['timestamp'].dt.tz_convert('Africa/Dar_es_Salaam')
    work['Hour (EAT)'], work['date'] = local.dt.hour, local.dt.date
    return work.groupby('Hour (EAT)').agg(**{
        'Median delay (min)': ('delay_mins', 'median'),
        'Observations': ('delay_mins', 'size'), 'Days': ('date', 'nunique')}).reset_index()
