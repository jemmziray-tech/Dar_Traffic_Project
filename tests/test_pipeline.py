import ast
from pathlib import Path
from unittest.mock import MagicMock
import pandas as pd
import pytest
import scrape_traffic as collector
from utils import fresh_traffic_frame


def test_provider_measurements_are_not_inflated():
    result = collector.parse_traffic_element({
        'status': 'OK', 'duration': {'value': 90},
        'duration_in_traffic': {'value': 150}, 'distance': {'value': 2000},
    })
    assert result == dict(normal_mins=1.5, live_mins=2.5, delay_mins=1.0,
                          speed_kmh=48.0, distance_km=2.0)


def test_missing_traffic_is_not_fabricated():
    with pytest.raises(KeyError):
        collector.parse_traffic_element({'status': 'OK', 'duration': {'value': 60},
                                         'distance': {'value': 1000}})


def test_failed_provider_writes_nothing(monkeypatch):
    maps, db = MagicMock(), MagicMock()
    maps.distance_matrix.return_value = {'status': 'REQUEST_DENIED'}
    monkeypatch.setattr(collector, 'gmaps', maps)
    monkeypatch.setattr(collector, 'db', db)
    assert collector.update_smart_city({'id': 'ubungo', 'start': 'a', 'end': 'b'}, ('Unknown', 0)) is False
    db.batch.assert_not_called()


def test_success_writes_live_and_history_atomically(monkeypatch):
    maps, db = MagicMock(), MagicMock()
    maps.distance_matrix.return_value = {'status': 'OK', 'rows': [{'elements': [{
        'status': 'OK', 'duration': {'value': 90},
        'duration_in_traffic': {'value': 150}, 'distance': {'value': 2000},
    }]}]}
    monkeypatch.setattr(collector, 'gmaps', maps)
    monkeypatch.setattr(collector, 'db', db)
    assert collector.update_smart_city({'id': 'ubungo', 'name': 'Ubungo', 'start': 'a', 'end': 'b'}, ('28 C, Clear', 0))
    assert db.batch.return_value.set.call_count == 2
    db.batch.return_value.commit.assert_called_once()


def test_old_and_unverified_rows_are_hidden():
    now = pd.Timestamp.now(tz='UTC')
    data = pd.DataFrame([
        dict(id='fresh', timestamp=now, schema_version=2, traffic_observed=True),
        dict(id='stale', timestamp=now-pd.Timedelta(hours=2), schema_version=2, traffic_observed=True),
        dict(id='legacy', timestamp=now, schema_version=1, traffic_observed=True),
        dict(id='estimated', timestamp=now, schema_version=2, traffic_observed=False),
    ])
    assert fresh_traffic_frame(data)['id'].tolist() == ['fresh']


def test_prediction_features_match_training_contract():
    # Extract the pure feature builder without importing the Streamlit page.
    module = ast.parse(Path('pages/4_AI_Predictor.py').read_text(encoding='utf-8'))
    function = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == 'build_features_df')
    scope = {'pd': pd, 'DAYS_MAP': {'Monday': 0}}
    exec(compile(ast.Module(body=[function], type_ignores=[]), '<feature builder>', 'exec'), scope)
    result = scope['build_features_df'](['ubungo'], 'Monday', 8, 'Rainy')
    assert result.columns.tolist() == ['road_id', 'hour', 'day_of_week', 'is_weekend',
                                     'is_rush_hour', 'temp_c', 'is_raining',
                                     'precipitation_mm', 'previous_delay']
