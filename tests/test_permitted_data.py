import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import live_api
from permitted_data import day_expiry, merge_day, training_records, validate_observation

NOW = datetime(2026, 10, 31, 9, tzinfo=timezone.utc)


@pytest.fixture
def source():
    return {
        "id": "test-survey",
        "enabled": True,
        "kind": "own_measurements",
        "rights_reference": "Fixture only; not a real dataset",
        "allowed_purposes": ["history", "public_display", "training"],
        "derived_from_google_maps": False,
        "retention_days": 90,
    }


def measurement(identifier="journey-1", stamp=None):
    return {
        "observation_id": identifier,
        "road_id": "mwenge",
        "timestamp": (stamp or NOW - timedelta(minutes=30)).isoformat(),
        "travel_minutes": 12.5,
        "distance_km": 3.0,
    }


def test_import_keeps_missing_baseline_unknown_and_is_repeatable(source):
    first = validate_observation(measurement(), source, NOW)
    second = validate_observation(measurement(), source, NOW)
    assert first["record_id"] == second["record_id"]
    assert first["baseline_minutes"] is None
    assert len(merge_day([], [first, second], NOW)["observations"]) == 1


@pytest.mark.parametrize(
    "change",
    [
        {"enabled": False},
        {"rights_reference": ""},
        {"derived_from_google_maps": True},
        {"kind": "google_distance_matrix"},
        {"allowed_purposes": ["training"]},
    ],
)
def test_import_rejects_unreviewed_or_google_derived_data(source, change):
    with pytest.raises(ValueError):
        validate_observation(measurement(), source | change, NOW)


def test_personal_trace_fields_are_not_accepted(source):
    with pytest.raises(ValueError, match="aggregated"):
        validate_observation(measurement() | {"driver_id": "someone"}, source, NOW)


def test_daily_expiry_does_not_move_with_late_appends(source):
    early = validate_observation(measurement("early", NOW - timedelta(hours=4)), source, NOW)
    late = validate_observation(measurement("late", NOW), source, NOW)
    assert merge_day([], [early], NOW)["expire_at"] == merge_day([early], [late], NOW)["expire_at"]
    assert day_expiry(early["timestamp"]) <= early["timestamp"] + timedelta(days=30)


def test_private_training_data_never_enters_public_summaries(source):
    source["allowed_purposes"] = ["history", "training"]
    record = validate_observation(measurement(), source, NOW)
    assert merge_day([], [record], NOW) is None
    assert training_records([record], {source["id"]: source}, NOW) == [record]


def test_revoking_training_permission_blocks_later_exports(source):
    record = validate_observation(measurement(), source, NOW)
    assert training_records([record], {source["id"]: source | {"enabled": False}}, NOW) == []
    assert (
        training_records(
            [record | {"source_kind": "google_distance_matrix"}], {source["id"]: source}, NOW
        )
        == []
    )
    assert training_records([record | {"expire_at": NOW}], {source["id"]: source}, NOW) == []


def test_live_budget_records_only_usage_and_blocks_overlapping_requests(monkeypatch):
    db = MagicMock()
    reference = db.collection.return_value.document.return_value
    reference.get.return_value.to_dict.return_value = {}
    monkeypatch.setattr(live_api.firestore, "transactional", lambda function: function)
    live_api.reserve_request(db, NOW)
    state = db.transaction.return_value.set.call_args.args[1]
    assert set(state) == {"elements", "requests", "next_request_at", "expire_at"}
    reference.get.return_value.to_dict.return_value = state
    with pytest.raises(live_api.BudgetExceeded):
        live_api.reserve_request(db, NOW)


def test_daily_provider_budget_is_checked_before_any_google_calls(monkeypatch):
    db = MagicMock()
    db.collection.return_value.document.return_value.get.return_value.to_dict.return_value = {
        "elements": 714
    }
    monkeypatch.setattr(live_api.firestore, "transactional", lambda function: function)
    with pytest.raises(live_api.BudgetExceeded):
        live_api.reserve_request(db, NOW)
    db.transaction.return_value.set.assert_not_called()


def test_live_wire_format_preserves_numeric_values_and_timestamps():
    encoded = live_api.wire_document({"timestamp": NOW, "live_mins": 2.5, "traffic_observed": True})
    assert encoded["fields"]["timestamp"] == {"timestampValue": NOW.isoformat()}
    assert encoded["fields"]["live_mins"] == {"doubleValue": 2.5}
    assert encoded["fields"]["traffic_observed"] == {"booleanValue": True}


def test_python_import_and_website_share_the_real_firestore_wire_format(source):
    from google.cloud.firestore_v1._helpers import encode_dict
    from google.cloud.firestore_v1.types import Document
    from google.protobuf.json_format import MessageToDict

    record = validate_observation(measurement(), source, NOW)
    wire = MessageToDict(Document(fields=encode_dict(record))._pb)
    fixture = Path(__file__).resolve().parents[1] / "web/tests/fixtures/permitted-history.json"
    assert wire == json.loads(fixture.read_text(encoding="utf-8"))


def test_cleanup_keeps_independent_or_mixed_documents():
    from scripts.retire_google_history import google_only

    document = MagicMock()
    document.to_dict.return_value = {"source": "google_distance_matrix"}
    assert google_only(document)
    document.to_dict.return_value = {"source": "independent_survey"}
    assert not google_only(document)
    document.to_dict.return_value = {
        "observations": [{"source": "google_distance_matrix"}, {"source": "independent_survey"}]
    }
    assert not google_only(document)
