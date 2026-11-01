"""Export only unexpired independent observations with explicit training permission."""

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from permitted_data import training_records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    db = firestore.Client(project="dar-traffic")
    query = db.collection("permitted_observations").where(
        filter=FieldFilter("expire_at", ">", datetime.now(timezone.utc))
    )
    registry = json.loads(
        (Path(__file__).resolve().parents[1] / "data_sources.json").read_text(encoding="utf-8")
    )
    sources = {source["id"]: source for source in registry["sources"]}
    records = training_records([document.to_dict() for document in query.stream()], sources)
    if not records:
        raise SystemExit("No unexpired observations have training permission. No file was written.")
    fields = [
        "record_id",
        "road_id",
        "timestamp",
        "travel_minutes",
        "distance_km",
        "source_id",
        "rights_reference",
    ]
    with args.output.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    print(
        f"Exported {len(records)} permitted observations. Keep source permissions with this dataset."
    )


if __name__ == "__main__":
    main()
