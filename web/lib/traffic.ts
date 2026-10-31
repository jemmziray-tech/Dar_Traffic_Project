import configuredRoads from "./roads.json";

export type Road = { id: string; name: string; start: string; end: string };
export type Observation = {
  roadId: string;
  name: string;
  timestamp: number;
  trafficMinutes: number;
  baselineMinutes: number;
  delayMinutes: number;
  distanceKm: number;
  speedKmh: number;
  weather: string;
};
export type FirestoreDocument = {
  name?: string;
  fields?: Record<string, Record<string, unknown>>;
};
export const ROADS: Road[] = configuredRoads;
export const FRESH_MS = 90 * 60 * 1000;
const roadIndex = new Map(ROADS.map((road) => [road.id, road]));

export function decode(value: Record<string, unknown>): unknown {
  if ("stringValue" in value) return value.stringValue;
  if ("booleanValue" in value) return value.booleanValue;
  if ("integerValue" in value) return Number(value.integerValue);
  if ("doubleValue" in value) return Number(value.doubleValue);
  if ("timestampValue" in value)
    return Date.parse(String(value.timestampValue));
  if ("nullValue" in value) return null;
  return undefined;
}

export function normalize(
  documents: FirestoreDocument[],
  now = Date.now(),
): Observation[] {
  const output: Observation[] = [];
  const seen = new Set<string>();
  for (const document of documents) {
    const values = Object.fromEntries(
      Object.entries(document.fields ?? {}).map(([key, value]) => [
        key,
        decode(value),
      ]),
    );
    const road = roadIndex.get(String(values.road_id));
    const timestamp = Number(values.timestamp),
      travel = Number(values.live_mins);
    const baseline = Number(values.normal_mins),
      distance = Number(values.distance_km);
    const delay = Number(values.delay_mins);
    if (
      !road ||
      values.schema_version !== 2 ||
      values.traffic_observed !== true ||
      values.source !== "google_distance_matrix"
    )
      continue;
    if (typeof values.timestamp !== "number" || timestamp <= 0) continue;
    if (![timestamp, travel, baseline, distance, delay].every(Number.isFinite))
      continue;
    if (
      travel <= 0 ||
      baseline <= 0 ||
      distance <= 0 ||
      delay < 0 ||
      timestamp > now
    )
      continue;
    if (Math.abs(delay - Math.max(0, travel - baseline)) > 0.021) continue;
    const key = `${road.id}:${timestamp}`;
    if (seen.has(key)) continue;
    seen.add(key);
    output.push({
      roadId: road.id,
      name: road.name,
      timestamp,
      trafficMinutes: travel,
      baselineMinutes: baseline,
      distanceKm: distance,
      delayMinutes: delay,
      speedKmh: distance / (travel / 60),
      weather: typeof values.weather === "string" ? values.weather : "Unknown",
    });
  }
  return output.sort((a, b) => a.timestamp - b.timestamp);
}

export function latest(records: Observation[]): Observation[] {
  const byRoad = new Map<string, Observation>();
  for (const record of records) {
    if (
      !byRoad.has(record.roadId) ||
      byRoad.get(record.roadId)!.timestamp < record.timestamp
    )
      byRoad.set(record.roadId, record);
  }
  return [...byRoad.values()];
}

export function isFresh(record: Observation, now = Date.now()) {
  return now - record.timestamp >= 0 && now - record.timestamp <= FRESH_MS;
}
export function median(values: number[]) {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b),
    middle = Math.floor(sorted.length / 2);
  return sorted.length % 2
    ? sorted[middle]
    : (sorted[middle - 1] + sorted[middle]) / 2;
}
export function minutes(value: number) {
  return value.toLocaleString("en", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 0,
  });
}
export function eat(timestamp: number, date = false) {
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "Africa/Dar_es_Salaam",
    ...(date ? { day: "numeric", month: "short" } : {}),
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(timestamp);
}
export function age(timestamp: number, now = Date.now()) {
  const minutes = Math.max(0, Math.floor((now - timestamp) / 60000));
  return minutes < 1
    ? "Just recorded"
    : minutes < 60
      ? `${minutes} min ago`
      : minutes < 1440
        ? `${Math.floor(minutes / 60)}h ${minutes % 60}m ago`
        : `${Math.floor(minutes / 1440)} days ago`;
}
export function directions(road: Road) {
  return `https://www.google.com/maps/dir/?${new URLSearchParams({ api: "1", origin: road.start, destination: road.end, travelmode: "driving" })}`;
}
export function csv(records: Observation[]) {
  const rows: (string | number)[][] = [
    [
      "Corridor",
      "Observed UTC",
      "Traffic minutes",
      "Baseline minutes",
      "Extra delay minutes",
      "Distance km",
      "Weather",
    ],
    ...records.map((record) => [
      record.name,
      new Date(record.timestamp).toISOString(),
      record.trafficMinutes,
      record.baselineMinutes,
      record.delayMinutes,
      record.distanceKm,
      record.weather,
    ]),
  ];
  return rows
    .map((row) =>
      row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(","),
    )
    .join("\r\n");
}

const endpoint =
  "https://firestore.googleapis.com/v1/projects/dar-traffic/databases/(default)/documents:runQuery";
const cache = new Map<string, { at: number; records: Observation[] }>();
const pending = new Map<string, Promise<Observation[]>>();
export async function readTraffic(
  history = false,
  force = false,
): Promise<Observation[]> {
  const collection = history ? "traffic_history" : "live_traffic";
  const cached = cache.get(collection);
  if (!force && cached && Date.now() - cached.at < (history ? 300000 : 60000))
    return cached.records;
  if (pending.has(collection)) return pending.get(collection)!;
  const promise = (async () => {
    const controller = new AbortController(),
      timer = setTimeout(() => controller.abort(), 20000);
    try {
      const structuredQuery = {
        from: [{ collectionId: collection }],
        limit: history ? 5000 : 100,
        ...(history
          ? {
              orderBy: [
                { field: { fieldPath: "timestamp" }, direction: "DESCENDING" },
              ],
            }
          : {}),
      };
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ structuredQuery }),
        signal: controller.signal,
        cache: "no-store",
      });
      if (!response.ok)
        throw new Error(
          "Traffic data is temporarily unavailable. Please try again.",
        );
      const body: { document?: FirestoreDocument }[] = await response.json();
      if (!Array.isArray(body))
        throw new Error("The data service returned an unexpected response.");
      const records = normalize(
        body.flatMap((entry) => (entry.document ? [entry.document] : [])),
      );
      cache.set(collection, { at: Date.now(), records });
      return records;
    } finally {
      clearTimeout(timer);
      pending.delete(collection);
    }
  })();
  pending.set(collection, promise);
  return promise;
}
