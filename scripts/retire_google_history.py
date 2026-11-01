"""Inventory old Google-derived documents. Deletion requires an explicit --apply."""

import argparse
import json

from google.cloud import firestore

COLLECTIONS = ("live_traffic", "traffic_history", "daily_history")


def google_only(document):
    value = document.to_dict() or {}
    if value.get("source") == "google_distance_matrix":
        return True
    observations = value.get("observations", [])
    return bool(observations) and all(
        row.get("source") == "google_distance_matrix" for row in observations
    )


def inventory(database):
    return {
        name: [document for document in database.collection(name).stream() if google_only(document)]
        for name in COLLECTIONS
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-project")
    args = parser.parse_args()
    if args.apply and args.confirm_project != "dar-traffic":
        raise SystemExit("Deletion needs --confirm-project dar-traffic and an approved inventory.")
    database = firestore.Client(project="dar-traffic")
    documents = inventory(database)
    print(json.dumps({name: len(rows) for name, rows in documents.items()}))
    if args.apply:
        # Re-check each document before deleting it; unrelated observations stay untouched.
        for rows in documents.values():
            for document in rows:
                if google_only(document.reference.get()):
                    document.reference.delete()
        print("Retired the inventoried Google-derived records.")
    else:
        print("Inventory only. No records were deleted.")


if __name__ == "__main__":
    main()
