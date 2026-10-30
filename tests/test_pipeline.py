import ast
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import scrape_traffic as collector


def test_provider_measurements_are_not_inflated():
    result = collector.parse_traffic_element(
        {
            "status": "OK",
            "duration": {"value": 90},
            "duration_in_traffic": {"value": 150},
            "distance": {"value": 2000},
        }
    )
    assert result == dict(
        normal_mins=1.5, live_mins=2.5, delay_mins=1.0, speed_kmh=48.0, distance_km=2.0
    )


def test_missing_traffic_is_not_fabricated():
    with pytest.raises(KeyError):
        collector.parse_traffic_element(
            {"status": "OK", "duration": {"value": 60}, "distance": {"value": 1000}}
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, 0])
def test_invalid_provider_measurements_are_rejected(value):
    with pytest.raises(ValueError):
        collector.parse_traffic_element(
            {
                "status": "OK",
                "duration": {"value": 90},
                "duration_in_traffic": {"value": value},
                "distance": {"value": 2000},
            }
        )


@pytest.mark.parametrize(
    "code,condition",
    [
        (0, "Clear"),
        (3, "Cloudy"),
        (45, "Fog"),
        (51, "Drizzle"),
        (63, "Rain"),
        (75, "Snow"),
        (97, "Thunderstorm"),
    ],
)
def test_weather_conditions_follow_provider_codes(code, condition):
    weather, rain = collector.parse_weather(
        {"temperature_2m": 26, "weather_code": code, "precipitation": 0.5}
    )
    assert weather == f"26°C, {condition}"
    assert rain == 0.5


@pytest.mark.parametrize(
    "current",
    [
        {},
        None,
        {"temperature_2m": 26},
        {"temperature_2m": float("nan"), "weather_code": 0, "precipitation": 0},
        {"temperature_2m": 26, "weather_code": 0, "precipitation": None},
    ],
)
def test_missing_weather_is_not_replaced_with_clear_sky(current):
    assert collector.parse_weather(current) == ("Unknown", None)


def test_weather_location_mismatch_is_not_reused_for_all_roads(monkeypatch):
    response = MagicMock()
    response.json.return_value = {
        "current": {"temperature_2m": 26, "weather_code": 0, "precipitation": 0}
    }
    monkeypatch.setattr(collector.requests, "get", MagicMock(return_value=response))
    roads = [{"id": "first", "start": "-6.7,39.2"}, {"id": "second", "start": "-6.8,39.3"}]
    assert collector.get_weather_for_all_roads(roads) == {
        "first": ("Unknown", None),
        "second": ("Unknown", None),
    }


def test_weather_locations_keep_their_corresponding_values(monkeypatch):
    response = MagicMock()
    response.json.return_value = [
        {"current": {"temperature_2m": 26, "weather_code": 0, "precipitation": 0}},
        {"current": {"temperature_2m": 25, "weather_code": 63, "precipitation": 2}},
    ]
    monkeypatch.setattr(collector.requests, "get", MagicMock(return_value=response))
    roads = [{"id": "first", "start": "-6.7,39.2"}, {"id": "second", "start": "-6.8,39.3"}]
    assert collector.get_weather_for_all_roads(roads) == {
        "first": ("26°C, Clear", 0),
        "second": ("25°C, Rain", 2),
    }


def test_failed_provider_writes_nothing(monkeypatch):
    maps, db = MagicMock(), MagicMock()
    maps.distance_matrix.return_value = {"status": "REQUEST_DENIED"}
    monkeypatch.setattr(collector, "gmaps", maps)
    monkeypatch.setattr(collector, "db", db)
    assert (
        collector.collect_road({"id": "ubungo", "start": "a", "end": "b"}, ("Unknown", 0)) is False
    )
    db.batch.assert_not_called()


def test_success_writes_live_and_history_atomically(monkeypatch):
    maps, db = MagicMock(), MagicMock()
    maps.distance_matrix.return_value = {
        "status": "OK",
        "rows": [
            {
                "elements": [
                    {
                        "status": "OK",
                        "duration": {"value": 90},
                        "duration_in_traffic": {"value": 150},
                        "distance": {"value": 2000},
                    }
                ]
            }
        ],
    }
    monkeypatch.setattr(collector, "gmaps", maps)
    monkeypatch.setattr(collector, "db", db)
    assert collector.collect_road(
        {"id": "ubungo", "name": "Ubungo", "start": "a", "end": "b"}, ("28 C, Clear", 0)
    )
    assert db.batch.return_value.set.call_count == 2
    db.batch.return_value.commit.assert_called_once()


def test_forecasts_cannot_load_unvalidated_legacy_models():
    source = Path("dashboard.py").read_text(encoding="utf-8")
    module = ast.parse(source)
    function = next(
        n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "forecasts"
    )
    calls = [ast.unparse(n.func) for n in ast.walk(function) if isinstance(n, ast.Call)]
    assert not any("joblib" in name or "predict" in name for name in calls)
    assert "No validated forecasting model is published" in source


def test_collector_targets_only_fresh_project(monkeypatch):
    client = MagicMock()
    maps_client = MagicMock()
    monkeypatch.setattr(collector.firestore, "Client", client)
    monkeypatch.setattr(collector.googlemaps, "Client", maps_client)
    monkeypatch.setenv("MAPS_API_KEY", "test-key")
    monkeypatch.setenv("FIREBASE_KEY_JSON", '{"project_id":"dar-traffic-command"}')
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "dar-traffic-command")
    collector.initialize_clients()
    client.assert_called_once_with(project="dar-traffic")
    maps_client.assert_called_once()
