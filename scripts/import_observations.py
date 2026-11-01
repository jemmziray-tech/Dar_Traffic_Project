"""Check an independently sourced JSON file; write it only with --apply."""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google.cloud import firestore

from permitted_data import EAT, merge_day, validate_observation, validate_source

ROOT = Path(__file__).resolve().parents[1]


def import_records(rows, source, database=None):
    records = [validate_observation(row, source) for row in rows]
    grouped = defaultdict(list)
    for record in records:
        grouped[record["timestamp"].astimezone(EAT).date().isoformat()].append(record)
    for day, additions in grouped.items():
        merge_day([], additions)
        if database is None:
            continue
        reference = database.collection("permitted_daily_history").document(day)

        @firestore.transactional
        def write(transaction):
            # Read first: repeating a source file updates its own IDs instead of duplicating journeys.
            current = reference.get(transaction=transaction).to_dict() or {}
            summary = merge_day(current.get("observations", []), additions)
            if summary is not None:
                transaction.set(reference, summary)
            for record in additions:
                transaction.set(
                    database.collection("permitted_observations").document(record["record_id"]),
                    record,
                )

        write(database.transaction())
    return len(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--source", required=True)
    parser.add_argument(
        "--apply", action="store_true", help="Write validated records to dar-traffic"
    )
    args = parser.parse_args()
    registry = json.loads((ROOT / "data_sources.json").read_text(encoding="utf-8"))
    source = next((item for item in registry["sources"] if item["id"] == args.source), None)
    if source is None:
        raise SystemExit("Source is not registered. Review its permissions before importing.")
    validate_source(source)
    rows = json.loads(args.file.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or len(rows) > 400:
        raise SystemExit("Use a JSON array of at most 400 observations per import.")
    count = import_records(
        rows, source, firestore.Client(project="dar-traffic") if args.apply else None
    )
    print(
        f"{'Imported' if args.apply else 'Validated'} {count} observations. {'No database writes.' if not args.apply else ''}"
    )


if __name__ == "__main__":
    main()
