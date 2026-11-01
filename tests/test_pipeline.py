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


def test_failed_provider_does_not_return_a_fake_reading(monkeypatch):
    maps = MagicMock()
    maps.distance_matrix.return_value = {"status": "REQUEST_DENIED"}
    monkeypatch.setattr(collector, "gmaps", maps)
    with pytest.raises(ValueError):
        collector.fetch_road({"id": "ubungo", "start": "a", "end": "b"}, ("Unknown", None))


def test_success_returns_a_live_reading_without_a_database_client(monkeypatch):
    maps = MagicMock()
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
    observation = collector.fetch_road(
        {"id": "ubungo", "name": "Ubungo", "start": "a", "end": "b"}, ("Unknown", None)
    )
    assert observation["live_mins"] == 2.5
    assert observation["timestamp"].tzinfo is not None
    assert "expire_at" not in observation
    assert not hasattr(collector, "db")


def test_live_provider_disables_automatic_retries(monkeypatch):
    maps_client = MagicMock()
    monkeypatch.setattr(collector, "SingleAttemptMapsClient", maps_client)
    monkeypatch.setenv("MAPS_API_KEY", "test-key")
    collector.initialize_clients()
    assert maps_client.call_args.kwargs["retry_timeout"] == 60
    assert maps_client.call_args.kwargs["retry_over_query_limit"] is False


def test_sdk_sends_initial_request_but_never_retries():
    client = collector.SingleAttemptMapsClient(key="AIza" + "x" * 35, timeout=15, retry_timeout=60)
    response = MagicMock(status_code=503)
    client.session.get = MagicMock(return_value=response)
    with pytest.raises(collector.googlemaps.exceptions.Timeout):
        client.distance_matrix("a", "b")
    assert client.session.get.call_count == 1


def test_sdk_first_request_can_succeed():
    client = collector.SingleAttemptMapsClient(key="AIza" + "x" * 35, timeout=15, retry_timeout=60)
    response = MagicMock(status_code=200)
    response.json.return_value = {"status": "OK", "rows": []}
    client.session.get = MagicMock(return_value=response)
    assert client.distance_matrix("a", "b")["status"] == "OK"
    assert client.session.get.call_count == 1
