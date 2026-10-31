import assert from "node:assert/strict";
import test from "node:test";
import {
  csv,
  directions,
  FRESH_MS,
  isFresh,
  latest,
  median,
  normalize,
  ROADS,
  type FirestoreDocument,
} from "../lib/traffic";

const now = Date.parse("2026-10-31T09:00:00Z");
function document(
  overrides: Record<string, Record<string, unknown>> = {},
): FirestoreDocument {
  return {
    fields: {
      road_id: { stringValue: ROADS[0].id },
      schema_version: { integerValue: "2" },
      source: { stringValue: "google_distance_matrix" },
      traffic_observed: { booleanValue: true },
      timestamp: { timestampValue: new Date(now - 60000).toISOString() },
      live_mins: { doubleValue: 5.72 },
      normal_mins: { doubleValue: 5.65 },
      delay_mins: { doubleValue: 0.07 },
      distance_km: { doubleValue: 1.85 },
      ...overrides,
    },
  };
}

test("accepts provider precision without inventing additional delay", () => {
  const [record] = normalize(
    [document({ normal_mins: { doubleValue: 5.66 } })],
    now,
  );
  assert.equal(record.delayMinutes, 0.07);
  assert.equal(record.weather, "Unknown");
});

test("excludes legacy, unobserved, unknown, invalid and future records", () => {
  const invalid: Record<string, Record<string, unknown>>[] = [
    { schema_version: { integerValue: "1" } },
    { source: { stringValue: "simulation" } },
    { traffic_observed: { booleanValue: false } },
    { road_id: { stringValue: "not-a-configured-road" } },
    { timestamp: { timestampValue: new Date(now + 1).toISOString() } },
    { timestamp: { nullValue: null } },
    { live_mins: { doubleValue: "NaN" } },
    { normal_mins: { doubleValue: 0 } },
    { distance_km: { doubleValue: -1 } },
    { delay_mins: { doubleValue: 8 } },
  ];
  for (const fields of invalid)
    assert.equal(normalize([document(fields)], now).length, 0);
});

test("deduplicates observations and selects each road’s latest timestamp", () => {
  const older = document({
    timestamp: { timestampValue: new Date(now - 120000).toISOString() },
  });
  const records = normalize([document(), older, document()], now);
  assert.equal(records.length, 2);
  assert.equal(latest(records)[0].timestamp, now - 60000);
});

test("freshness includes the 90 minute boundary and rejects future timestamps", () => {
  const [record] = normalize([document()], now);
  assert.equal(isFresh({ ...record, timestamp: now - FRESH_MS }, now), true);
  assert.equal(
    isFresh({ ...record, timestamp: now - FRESH_MS - 1 }, now),
    false,
  );
  assert.equal(isFresh({ ...record, timestamp: now + 1 }, now), false);
});

test("median handles missing data and does not mutate observations", () => {
  const values = [9, 0, 2, 1];
  assert.equal(median([]), null);
  assert.equal(median(values), 1.5);
  assert.deepEqual(values, [9, 0, 2, 1]);
});

test("CSV preserves quoted road names, timestamps and measured precision", () => {
  const [record] = normalize([document()], now);
  const output = csv([{ ...record, name: 'Road, "A"' }]);
  assert.match(output, /"Road, ""A"""/);
  assert.match(output, /2026-10-31T08:59:00.000Z/);
  assert.match(output, /"0.07"/);
});

test("directions use the selected corridor’s actual endpoints", () => {
  const url = new URL(directions(ROADS[0]));
  assert.equal(url.hostname, "www.google.com");
  assert.equal(url.searchParams.get("origin"), ROADS[0].start);
  assert.equal(url.searchParams.get("destination"), ROADS[0].end);
});
