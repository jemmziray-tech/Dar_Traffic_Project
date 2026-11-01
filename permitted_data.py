"""Validate independently sourced journeys before history or training use."""

import hashlib
import json
import math
from datetime import datetime, timedelta, timezone

from config import ROAD_MAP

EAT = timezone(timedelta(hours=3))
PUBLIC_HISTORY_DAYS = 30
MAX_DAY_RECORDS = 1000
MAX_DAY_BYTES = 700_000


def utc_timestamp(value):
    stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("Observation timestamps must include a timezone")
    return stamp.astimezone(timezone.utc)


def validate_source(source):
    if source.get("enabled") is not True:
        raise ValueError("Enable a reviewed source in data_sources.json before importing")
    if source.get("kind") not in {"own_measurements", "licensed_dataset"}:
        raise ValueError("Only independent measurements or a licensed dataset can be imported")
    if not source.get("rights_reference") or not str(source.get("rights_reference")).strip():
        raise ValueError("A source needs a specific permission or ownership reference")
    purposes = set(source.get("allowed_purposes", []))
    if "history" not in purposes:
        raise ValueError("Permission must cover history storage")
    if source.get("derived_from_google_maps", True) is not False:
        raise ValueError("Google-derived traffic must not enter this history pipeline")
    days = source.get("retention_days")
    if not isinstance(days, int) or isinstance(days, bool) or not 1 <= days <= 365:
        raise ValueError("Set a permitted retention period between 1 and 365 days")
    return source


def validate_observation(row, source, now=None):
    validate_source(source)
    now = now or datetime.now(timezone.utc)
    # The import format deliberately has no driver, vehicle or GPS-trace fields.
    allowed = {
        "observation_id",
        "road_id",
        "timestamp",
        "travel_minutes",
        "distance_km",
        "baseline_minutes",
    }
    if set(row) - allowed:
        raise ValueError("Unexpected fields: import aggregated corridor measurements only")
    if row.get("road_id") not in ROAD_MAP:
        raise ValueError("Unknown corridor")
    if not isinstance(row.get("observation_id"), str) or not row["observation_id"].strip():
        raise ValueError("Each source observation needs a stable ID for safe repeated imports")
    stamp = utc_timestamp(row["timestamp"])
    if stamp > now or stamp <= datetime(2000, 1, 1, tzinfo=timezone.utc):
        raise ValueError("Invalid observation date")
    for field in ("travel_minutes", "distance_km"):
        value = row.get(field)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ValueError(f"{field} must be a finite positive measurement")
    baseline = row.get("baseline_minutes")
    if baseline is not None and (
        isinstance(baseline, bool)
        or not isinstance(baseline, (int, float))
        or not math.isfinite(baseline)
        or baseline <= 0
    ):
        raise ValueError("An optional baseline must be a finite positive independent value")
    expire_at = stamp + timedelta(days=source["retention_days"])
    if expire_at <= now:
        raise ValueError("This record is already outside its permitted retention period")
    identity = hashlib.sha256(f"{source['id']}:{row['observation_id']}".encode()).hexdigest()
    return {
        "record_id": identity,
        "schema_version": 3,
        "source_id": source["id"],
        "source_kind": source["kind"],
        "rights_reference": source["rights_reference"],
        "history_allowed": True,
        "public_display_allowed": "public_display" in source["allowed_purposes"],
        "training_allowed": "training" in source["allowed_purposes"],
        "derived_from_google_maps": False,
        "road_id": row["road_id"],
        "timestamp": stamp,
        "travel_minutes": row["travel_minutes"],
        "distance_km": row["distance_km"],
        "baseline_minutes": baseline,
        "expire_at": expire_at,
    }


def day_expiry(stamp):
    """Keep the cutoff fixed for the whole day; late appends cannot move it."""
    start = stamp.astimezone(EAT).replace(hour=0, minute=0, second=0, microsecond=0)
    return (start + timedelta(days=PUBLIC_HISTORY_DAYS)).astimezone(timezone.utc)


def merge_day(existing, incoming, now=None):
    now = now or datetime.now(timezone.utc)
    records = {record["record_id"]: record for record in existing + incoming}
    records = [
        record
        for record in records.values()
        if record.get("public_display_allowed") is True
        and record["expire_at"] > now
        and day_expiry(record["timestamp"]) > now
    ]
    records.sort(key=lambda record: (record["timestamp"], record["record_id"]))
    if not records:
        return None
    dates = {record["timestamp"].astimezone(EAT).date() for record in records}
    if len(dates) != 1:
        raise ValueError("A daily summary must contain just one Tanzania calendar day")
    if len(records) > MAX_DAY_RECORDS:
        raise ValueError("Daily history is full; partition it before increasing collection")
    summary = {
        "observations": records,
        "expire_at": min(
            day_expiry(records[0]["timestamp"]), *(record["expire_at"] for record in records)
        ),
    }
    if len(json.dumps(summary, default=str).encode()) > MAX_DAY_BYTES:
        raise ValueError("Daily history would exceed its safe size budget")
    return summary


def training_records(records, sources, now=None):
    now = now or datetime.now(timezone.utc)
    accepted = []
    for record in records:
        source = sources.get(record.get("source_id"), {})
        if (
            record.get("schema_version") == 3
            and record.get("training_allowed") is True
            and record.get("source_kind") in {"own_measurements", "licensed_dataset"}
            and record.get("derived_from_google_maps") is False
            and record.get("rights_reference")
            and record.get("expire_at", now) > now
            and source.get("enabled") is True
            and "training" in source.get("allowed_purposes", [])
            and source.get("derived_from_google_maps") is False
            and source.get("rights_reference") == record["rights_reference"]
        ):
            accepted.append(record)
    return accepted
