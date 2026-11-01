"""Serve a fresh Google estimate without writing its content to a database."""

import concurrent.futures
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from google.cloud import firestore

import scrape_traffic as provider
from config import ROADS

EAT = timezone(timedelta(hours=3))
PROJECT = "dar-traffic"
MAX_ELEMENTS_PER_DAY = 714
MIN_REQUEST_INTERVAL = timedelta(seconds=60)
ORIGINS = {"https://dartraffic.vercel.app", "https://dar-traffic.vercel.app"}
database = None


class BudgetExceeded(Exception):
    pass


def reserve_request(db, now=None):
    """Count requests, not traffic content. Keep usage within the old daily allowance."""
    now = now or datetime.now(timezone.utc)
    reference = db.collection("_live_usage").document(now.astimezone(EAT).date().isoformat())

    @firestore.transactional
    def reserve(transaction):
        state = reference.get(transaction=transaction).to_dict() or {}
        if state.get("next_request_at", now) > now:
            raise BudgetExceeded("A live request just ran. Please try again in a minute.")
        if state.get("elements", 0) + len(ROADS) > MAX_ELEMENTS_PER_DAY:
            raise BudgetExceeded("Today's live-request allowance is used. Please return tomorrow.")
        transaction.set(
            reference,
            {
                "elements": state.get("elements", 0) + len(ROADS),
                "requests": state.get("requests", 0) + 1,
                "next_request_at": now + MIN_REQUEST_INTERVAL,
                "expire_at": now + timedelta(days=2),
            },
        )

    reserve(db.transaction())


def wire_document(observation):
    """Use the same typed values as the existing reader, including real timestamps."""
    fields = {}
    for key, value in observation.items():
        if isinstance(value, datetime):
            fields[key] = {"timestampValue": value.isoformat()}
        elif isinstance(value, bool):
            fields[key] = {"booleanValue": value}
        elif isinstance(value, int):
            fields[key] = {"integerValue": str(value)}
        elif isinstance(value, float):
            fields[key] = {"doubleValue": value}
        elif value is None:
            fields[key] = {"nullValue": None}
        else:
            fields[key] = {"stringValue": value}
    return {"fields": fields}


def live_documents():
    weather = provider.get_weather_for_all_roads(ROADS)

    def fetch(road):
        try:
            return wire_document(
                provider.fetch_road(road, weather.get(road["id"], ("Unknown", None)))
            )
        except Exception as error:
            # Provider exceptions can contain request URLs. Do not log keys or full URLs.
            logging.warning(
                "Live estimate unavailable for %s (%s)", road["id"], type(error).__name__
            )
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        return [document for document in executor.map(fetch, ROADS) if document is not None]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logging.info("HTTP %s", args[1] if len(args) > 1 else "request")

    def respond(self, status, body):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store, private")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(payload)))
        origin = self.headers.get("Origin", "")
        if (
            origin in ORIGINS
            or origin.startswith("http://127.0.0.1:")
            or origin.startswith("http://localhost:")
        ):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        if status == 429:
            self.send_header("Retry-After", "60")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/health":
            self.respond(
                200,
                {
                    "status": "ok",
                    "mode": "live_only",
                    "stores_google_history": False,
                    "revision": os.getenv("K_REVISION", "local"),
                },
            )
            return
        if self.path != "/live":
            self.respond(404, {"error": "Not found"})
            return
        try:
            reserve_request(database)
            documents = live_documents()
            if not documents:
                self.respond(503, {"error": "No live estimates are available. Please try later."})
                return
            self.respond(200, {"documents": documents, "history_stored": False})
        except BudgetExceeded as error:
            self.respond(429, {"error": str(error)})
        except Exception as error:
            logging.error("Live request failed (%s)", type(error).__name__)
            self.respond(503, {"error": "Live estimates are temporarily unavailable."})


def main():
    global database
    logging.basicConfig(level=logging.INFO)
    provider.initialize_clients()
    database = firestore.Client(project=PROJECT)
    ThreadingHTTPServer(("0.0.0.0", int(os.getenv("PORT", "8080"))), Handler).serve_forever()


if __name__ == "__main__":
    main()
