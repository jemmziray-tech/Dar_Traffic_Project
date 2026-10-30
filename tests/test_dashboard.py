from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from navigation import PAGE_ROUTES
from traffic_data import hourly_profile, observations, recent, scenario

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["app.py", *[path for path, _, _ in PAGE_ROUTES[1:]]]


def record(road="mwenge", **overrides):
    row = dict(
        road_id=road,
        timestamp=pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=5),
        schema_version=2,
        traffic_observed=True,
        source="google_distance_matrix",
        live_mins=12.0,
        normal_mins=10.0,
        distance_km=3.0,
        weather="Unknown",
    )
    return dict(row, **overrides)


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("state", ["data", "empty", "failure"])
def test_all_pages_render_for_data_empty_and_outage(page, state):
    rows = [record(), record("ubungo")] if state == "data" else []

    def read(history=False):
        return observations(rows), len(rows), "Database unavailable" if state == "failure" else None

    with patch("dashboard.read_data", side_effect=read):
        app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
        if page != "app.py":
            app.switch_page(page.replace("\\", "/")).run(timeout=30)
    assert not app.exception, "\n".join(str(x.value) for x in app.exception)


def test_live_search_and_scenario_controls():
    with patch("dashboard.read_data", return_value=(observations([record()]), 1, None)):
        app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
        app.text_input[0].set_value("missing corridor").run()
        assert not app.exception
        assert app.dataframe[0].value.empty
        lab = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
        lab.switch_page("pages/scenarios.py").run(timeout=30)
        lab.slider[0].set_value(100).run()
        assert not lab.exception
        assert lab.metric[1].value == "20.00 min"
        lab.radio[0].set_value("Use a recent corridor observation").run()
        assert not lab.exception
        assert lab.metric[1].value == "10.00 min"


def test_invalid_measurements_and_stale_records_cannot_be_current():
    now = pd.Timestamp.now(tz="UTC")
    rows = [
        record(),
        record("ubungo", live_mins=float("inf")),
        record("ubungo", timestamp=now + pd.Timedelta(minutes=1)),
        record("ubungo", schema_version=1),
        record("ubungo", source="synthetic"),
        record("ubungo", timestamp=now - pd.Timedelta(hours=2)),
    ]
    result = observations(rows, now=now)
    assert len(result) == 2
    assert list(recent(result).road_id) == ["mwenge"]
    assert recent(result).iloc[0].delay_mins == 2
    assert recent(result).iloc[0].speed_kmh == 15


def test_scenario_never_reduces_baseline_or_invents_negative_delay():
    assert scenario(30, 20, 100) == (20, 10)
    assert scenario(18, 20, 100) == (18, 0)
    assert scenario(30, 20, 0) == (30, 0)


def test_delay_preserves_collector_precision_and_rejects_inflation():
    frame = observations([record(live_mins=3.84, normal_mins=3.78, delay_mins=0.07)])
    assert frame.iloc[0].delay_mins == 0.07
    assert observations([record(delay_mins=15)]).empty


def test_hourly_profile_reports_sample_support_not_interpolated_hours():
    frame = observations(
        [
            record(timestamp=pd.Timestamp("2026-10-29T06:00:00Z")),
            record(timestamp=pd.Timestamp("2026-10-30T06:00:00Z")),
        ]
    )
    profile = hourly_profile(frame)
    assert list(profile["Hour (EAT)"]) == [9]
    assert profile.iloc[0]["Days"] == 2
    assert profile.iloc[0]["Observations"] == 2
