"""Read-only Firestore REST client for public traffic observations."""

from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import datetime

import requests

ALLOWED_COLLECTIONS = frozenset({"live_traffic", "traffic_history"})


def decode_value(value):
    if "timestampValue" in value:
        return datetime.fromisoformat(value["timestampValue"].replace("Z", "+00:00"))
    if "integerValue" in value:
        return int(value["integerValue"])
    if "doubleValue" in value:
        return float(value["doubleValue"])
    if "arrayValue" in value:
        return [decode_value(v) for v in value["arrayValue"].get("values", [])]
    if "mapValue" in value:
        return {k: decode_value(v) for k, v in value["mapValue"].get("fields", {}).items()}
    for key in ("stringValue", "booleanValue", "nullValue"):
        if key in value:
            return value[key]
    raise ValueError("Unsupported Firestore field type")


@dataclass(frozen=True)
class TrafficDocument:
    id: str
    data: dict

    def to_dict(self):
        return deepcopy(self.data)


@dataclass(frozen=True)
class TrafficQuery:
    collection_id: str
    count: int = 5000
    ordering: tuple | None = None
    equality: tuple | None = None

    def limit(self, count):
        if not 1 <= count <= 5000:
            raise ValueError("Traffic query limit must be between 1 and 5000")
        return replace(self, count=count)

    def order_by(self, field, direction="ASCENDING"):
        if field != "timestamp" or direction not in ("ASCENDING", "DESCENDING"):
            raise ValueError("Only timestamp ordering is supported")
        return replace(self, ordering=(field, direction))

    def where(self, field, operation, value):
        if field != "road_id" or operation != "==" or not isinstance(value, str):
            raise ValueError("Only road_id equality filtering is supported")
        return replace(self, equality=(field, value))

    def stream(self):
        query = {"from": [{"collectionId": self.collection_id}], "limit": self.count}
        if self.ordering:
            field, direction = self.ordering
            query["orderBy"] = [{"field": {"fieldPath": field}, "direction": direction}]
        if self.equality:
            field, value = self.equality
            query["where"] = {
                "fieldFilter": {
                    "field": {"fieldPath": field},
                    "op": "EQUAL",
                    "value": {"stringValue": value},
                }
            }
        response = requests.post(
            "https://firestore.googleapis.com/v1/projects/dar-traffic/databases/(default)/documents:runQuery",
            json={"structuredQuery": query},
            timeout=25,
        )
        response.raise_for_status()
        for entry in response.json():
            document = entry.get("document")
            if document:
                yield TrafficDocument(
                    document["name"].rsplit("/", 1)[-1],
                    {k: decode_value(v) for k, v in document.get("fields", {}).items()},
                )


class PublicTrafficReader:
    """Exposes no write methods, credentials, or arbitrary project selection."""

    project = "dar-traffic"

    def collection(self, name):
        if name not in ALLOWED_COLLECTIONS:
            raise ValueError("Only public traffic collections are supported")
        return TrafficQuery(name)
