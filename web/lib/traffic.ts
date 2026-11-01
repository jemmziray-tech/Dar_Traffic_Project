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
export type HistoryObservation = Omit<Observation, "baselineMinutes" | "delayMinutes"> & {
  baselineMinutes: number | null;
  delayMinutes: number | null;
  expiresAt: number;
  sourceId: string;
  rightsReference: string;
  trainingAllowed: boolean;
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
export function csv(records: HistoryObservation[]) {
  const rows: (string | number | boolean | null)[][] = [
    ["Corridor", "Observed UTC", "Travel minutes", "Reference minutes", "Extra delay minutes", "Distance km", "Source", "Rights reference", "Training permitted"],
    ...records.map(record => [record.name, new Date(record.timestamp).toISOString(), record.trafficMinutes,
      record.baselineMinutes, record.delayMinutes, record.distanceKm, record.sourceId, record.rightsReference, record.trainingAllowed]),
  ];
  return rows.map(row => row.map(cell => `"${String(cell ?? "").replaceAll('"', '""')}"`).join(",")).join("\r\n");
}

const endpoint =
  "https://firestore.googleapis.com/v1/projects/dar-traffic/databases/(default)/documents:runQuery";
const pendingLive: { request?: Promise<Observation[]> } = {};
const pendingHistory: { request?: Promise<HistoryObservation[]> } = {};
let historyCache: { at: number; records: HistoryObservation[] } | undefined;
export const LIVE_API_URL = "https://dar-traffic-live-tvpcat636q-bq.a.run.app";
export const HISTORY_DAYS = 30;

export function dailyObservations(documents: FirestoreDocument[]): FirestoreDocument[] {
  return documents.flatMap(document => {
    const array = document.fields?.observations?.arrayValue as { values?: { mapValue?: FirestoreDocument }[] } | undefined;
    return (array?.values ?? []).flatMap(value => value.mapValue ? [value.mapValue] : []);
  });
}

export function normalizeHistory(documents: FirestoreDocument[], now = Date.now()): HistoryObservation[] {
  const records: HistoryObservation[] = [];
  const seen = new Set<string>();
  for (const document of documents) {
    const value = Object.fromEntries(Object.entries(document.fields ?? {}).map(([key, field]) => [key, decode(field)]));
    const road = roadIndex.get(String(value.road_id));
    const timestamp = value.timestamp, expiry = value.expire_at;
    const travel = value.travel_minutes, distance = value.distance_km;
    const baseline = value.baseline_minutes ?? null;
    if (!road || value.schema_version !== 3 || value.history_allowed !== true || value.public_display_allowed !== true || value.derived_from_google_maps !== false) continue;
    if (!["own_measurements", "licensed_dataset"].includes(String(value.source_kind)) || typeof value.rights_reference !== "string" || !value.rights_reference.trim()) continue;
    if (typeof timestamp !== "number" || timestamp > now || timestamp < now - HISTORY_DAYS * 86400000 || timestamp <= 0) continue;
    if (typeof expiry !== "number" || !Number.isFinite(expiry) || expiry <= now) continue;
    if (typeof travel !== "number" || !Number.isFinite(travel) || travel <= 0 || typeof distance !== "number" || !Number.isFinite(distance) || distance <= 0) continue;
    if (baseline !== null && (typeof baseline !== "number" || !Number.isFinite(baseline) || baseline <= 0)) continue;
    if (typeof value.record_id !== "string" || seen.has(value.record_id) || typeof value.source_id !== "string") continue;
    seen.add(value.record_id);
    records.push({ roadId: road.id, name: road.name, timestamp, trafficMinutes: travel,
      baselineMinutes: baseline as number | null,
      delayMinutes: baseline === null ? null : Math.max(0, travel - (baseline as number)),
      distanceKm: distance, speedKmh: distance / (travel / 60), weather: "Not supplied",
      expiresAt: expiry, sourceId: value.source_id, rightsReference: value.rights_reference, trainingAllowed: value.training_allowed === true });
  }
  return records.sort((a,b) => a.timestamp-b.timestamp);
}

async function requestJSON(url: string, options: RequestInit = {}) {
  const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 45000);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal, cache: "no-store" });
    const body = await response.json();
    if (!response.ok) throw new Error(typeof body.error === "string" ? body.error : "The data service is temporarily unavailable.");
    return body;
  } finally { clearTimeout(timer); }
}

export function readLive(): Promise<Observation[]> {
  if (pendingLive.request) return pendingLive.request;
  pendingLive.request = (async () => {
    try {
      const body = await requestJSON(`${LIVE_API_URL}/live`);
      if (!Array.isArray(body.documents)) throw new Error("The live service returned an unexpected response.");
      return normalize(body.documents);
    } finally { delete pendingLive.request; }
  })();
  return pendingLive.request;
}

export async function readHistory(force = false): Promise<HistoryObservation[]> {
  if (!force && historyCache && Date.now() - historyCache.at < 300000) {
    return historyCache.records.filter(record => record.timestamp >= Date.now() - HISTORY_DAYS * 86400000 && record.expiresAt > Date.now());
  }
  if (pendingHistory.request) return pendingHistory.request;
  pendingHistory.request = (async () => {
    try {
      const body = await requestJSON(endpoint, { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ structuredQuery: { from: [{ collectionId: "permitted_daily_history" }], limit: 31,
          orderBy: [{ field: { fieldPath: "__name__" }, direction: "DESCENDING" }] } }) });
      if (!Array.isArray(body)) throw new Error("The history service returned an unexpected response.");
      const records = normalizeHistory(dailyObservations(body.flatMap(entry => entry.document ? [entry.document] : [])));
      historyCache = {at: Date.now(), records};
      return records;
    } finally { delete pendingHistory.request; }
  })();
  return pendingHistory.request;
}
