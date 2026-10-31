from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

import scrape_traffic as collector


def lock_database(monkeypatch, state):
    database = MagicMock()
    reference = database.collection.return_value.document.return_value
    reference.get.return_value.to_dict.return_value = state
    monkeypatch.setattr(collector, "db", database)
    monkeypatch.setattr(collector.firestore, "transactional", lambda function: function)
    return database


@pytest.mark.parametrize("busy", ["same_slot", "active_lease"])
def test_duplicate_or_overlapping_collection_does_not_claim(monkeypatch, busy):
    now = datetime(2026, 10, 31, 6, 0, tzinfo=timezone.utc)
    state = (
        {"slot": int(now.timestamp()) // 1800}
        if busy == "same_slot"
        else {"lease_until": now + timedelta(minutes=5)}
    )
    database = lock_database(monkeypatch, state)
    assert collector.claim_collection(now) is None
    database.transaction.return_value.set.assert_not_called()


def test_new_slot_claim_is_written_transactionally(monkeypatch):
    now = datetime(2026, 10, 31, 6, 0, tzinfo=timezone.utc)
    database = lock_database(monkeypatch, {"lease_until": now - timedelta(minutes=1)})
    owner = collector.claim_collection(now)
    state = database.transaction.return_value.set.call_args.args[1]
    assert state["owner"] == owner
    assert state["slot"] == int(now.timestamp()) // 1800
    assert state["lease_until"] == now + timedelta(minutes=10)


def test_only_the_owner_can_release_a_collection(monkeypatch):
    database = lock_database(monkeypatch, {"owner": "another-run"})
    collector.release_collection("this-run")
    database.transaction.return_value.update.assert_not_called()


def test_duplicate_main_run_makes_no_provider_requests(monkeypatch):
    monkeypatch.setattr(collector, "initialize_clients", MagicMock())
    monkeypatch.setattr(collector, "claim_collection", lambda: None)
    weather = MagicMock()
    monkeypatch.setattr(collector, "get_weather_for_all_roads", weather)
    assert collector.main() == 0
    weather.assert_not_called()
