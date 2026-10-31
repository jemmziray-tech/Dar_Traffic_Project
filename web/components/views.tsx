"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  Bookmark,
  CalendarDays,
  Check,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Database,
  ExternalLink,
  Info,
  Radio,
  Route,
  Search,
  ShieldCheck,
  Timer,
  TrendingUp,
} from "lucide-react";
import {
  age,
  directions,
  eat,
  isFresh,
  latest,
  median,
  minutes,
  Observation,
  ROADS,
} from "@/lib/traffic";
import { useTraffic } from "./provider";
import {
  Download,
  Empty,
  Freshness,
  LocationTag,
  PageHeading,
  SaveButton,
  StatusPill,
  TrustNote,
} from "./ui";

function useRoadSelection() {
  const [roadId, setRoadId] = useState(ROADS[0].id);
  useEffect(() => {
    const value = new URLSearchParams(window.location.search).get("road");
    if (value && ROADS.some((road) => road.id === value)) setRoadId(value);
  }, []);
  function choose(value: string) {
    setRoadId(value);
    const url = new URL(window.location.href);
    url.searchParams.set("road", value);
    window.history.replaceState(null, "", url);
  }
  return [roadId, choose] as const;
}
function RoadPicker({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="select-label">
      <Route size={16} />
      <span className="sr-only">Choose a corridor</span>
      <select
        aria-label="Choose a corridor"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {ROADS.map((road) => (
          <option value={road.id} key={road.id}>
            {road.name}
          </option>
        ))}
      </select>
    </label>
  );
}
function Metric({
  label,
  value,
  unit,
  note,
  icon: Icon,
  accent = false,
}: {
  label: string;
  value: string;
  unit?: string;
  note: string;
  icon: typeof Route;
  accent?: boolean;
}) {
  return (
    <div className={`metric-card ${accent ? "accent" : ""}`}>
      <div className="metric-top">
        <span>{label}</span>
        <Icon size={18} />
      </div>
      <div className="metric-value">
        {value}
        <span>{unit}</span>
      </div>
      <p>{note}</p>
    </div>
  );
}

export function Overview() {
  const data = useTraffic(),
    all = latest(data.live),
    recent = all.filter((record) => isFresh(record, data.now));
  const [query, setQuery] = useState(""),
    [filter, setFilter] = useState("all"),
    [sort, setSort] = useState("delay"),
    [page, setPage] = useState(0);
  const byRoad = new Map(all.map((record) => [record.roadId, record]));
  const rows = ROADS.map((road) => ({
    road,
    record: byRoad.get(road.id),
  })).filter(
    ({ road, record }) =>
      road.name.toLowerCase().includes(query.toLowerCase()) &&
      (filter !== "saved" || data.saved.includes(road.id)) &&
      (filter !== "delay" ||
        (!!record && isFresh(record, data.now) && record.delayMinutes > 0)),
  );
  rows.sort((a, b) =>
    sort === "name"
      ? a.road.name.localeCompare(b.road.name)
      : sort === "time"
        ? (b.record?.trafficMinutes ?? -1) - (a.record?.trafficMinutes ?? -1)
        : (b.record?.delayMinutes ?? -1) - (a.record?.delayMinutes ?? -1),
  );
  const visible = rows.slice(page * 8, page * 8 + 8),
    worst = [...recent].sort((a, b) => b.delayMinutes - a.delayMinutes)[0];
  const typical = median(recent.map((record) => record.delayMinutes));
  return (
    <>
      <PageHeading
        eyebrow="THE CITY AT A GLANCE"
        title="A closer look at Dar’s roads."
        description="Traffic estimates, useful context, and a little less uncertainty."
        action={<LocationTag />}
      />
      <Freshness />
      <div className="metrics-grid">
        <Metric
          label="Recent corridors"
          value={data.loading && !all.length ? "—" : `${recent.length}`}
          unit={`/ ${ROADS.length}`}
          note="Observed within 90 minutes"
          icon={Radio}
          accent
        />
        <Metric
          label="Median extra delay"
          value={typical === null ? "—" : minutes(typical)}
          unit="min"
          note="Across recently observed corridors"
          icon={Clock3}
        />
        <Metric
          label="Largest extra delay"
          value={worst ? minutes(worst.delayMinutes) : "—"}
          unit="min"
          note={worst ? worst.name : "Waiting for a recent observation"}
          icon={TrendingUp}
        />
        <Metric
          label="Your saved corridors"
          value={String(data.saved.length)}
          note="Keep the roads you use close by"
          icon={Bookmark}
        />
      </div>
      <div className="overview-middle">
        <section className="spotlight">
          <div className="spotlight-kicker">
            <span className="status-dot" />
            CORRIDOR SPOTLIGHT
          </div>
          <div className="spotlight-body">
            <div>
              <h2>{worst ? worst.name : "Keep an eye on your route."}</h2>
              <p>
                {worst
                  ? "The largest additional delay in the latest recent observations."
                  : "Current conditions need a recent observation. Browse recorded history while the feed catches up."}
              </p>
              <Link
                className="button lime"
                href={worst ? `/corridors/?road=${worst.roadId}` : "/history/"}
              >
                {worst ? "Take a closer look" : "Browse history"}
                <ArrowUpRight size={16} />
              </Link>
            </div>
            {worst ? (
              <div className="spotlight-number">
                <span>EXTRA DELAY</span>
                <strong>
                  +{minutes(worst.delayMinutes)}
                  <small>min</small>
                </strong>
                <div>{minutes(worst.trafficMinutes)} min with traffic</div>
              </div>
            ) : (
              <Route size={78} className="spotlight-route" />
            )}
          </div>
          <div className="spotlight-bottom">
            <span>
              <span className="dot-outline" />
              Measured endpoint pairs
            </span>
            <span>
              Google traffic estimates <ArrowUpRight size={12} />
            </span>
          </div>
        </section>
        <section className="small-note">
          <div className="note-icon">
            <Info size={20} />
          </div>
          <h3>A number worth understanding.</h3>
          <p>
            “Extra delay” compares the traffic estimate with the provider’s
            baseline. Zero means they’re close—not that the road is empty.
          </p>
          <Link href="/about/">
            How we read the data <ArrowRight size={15} />
          </Link>
        </section>
      </div>
      <section className="panel corridor-panel">
        <div className="section-heading">
          <div>
            <div className="eyebrow small">THE ROADS YOU USE</div>
            <h2>
              Explore the corridors
              <span className="count-badge">{ROADS.length}</span>
            </h2>
          </div>
          <Download
            records={rows.flatMap((row) => (row.record ? [row.record] : []))}
          />
        </div>
        <div className="table-controls">
          <div className="segmented" aria-label="Filter corridors">
            {[
              ["all", "All corridors"],
              ["delay", "Added delay"],
              ["saved", "Saved"],
            ].map(([id, label]) => (
              <button
                key={id}
                className={filter === id ? "active" : ""}
                aria-pressed={filter === id}
                onClick={() => {
                  setFilter(id);
                  setPage(0);
                }}
              >
                {id === "saved" && <Bookmark size={13} />} {label}
                {id === "saved" && data.saved.length > 0 && (
                  <small>{data.saved.length}</small>
                )}
              </button>
            ))}
          </div>
          <div className="search-sort">
            <label className="search-field">
              <Search size={16} />
              <input
                placeholder="Find a road…"
                aria-label="Find a road"
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setPage(0);
                }}
              />
            </label>
            <label className="sort-field">
              <ArrowDown size={14} />
              <select
                aria-label="Sort corridors"
                value={sort}
                onChange={(event) => {
                  setSort(event.target.value);
                  setPage(0);
                }}
              >
                <option value="delay">Extra delay</option>
                <option value="name">Road name</option>
                <option value="time">Travel time</option>
              </select>
            </label>
          </div>
        </div>
        {!rows.length ? (
          <Empty
            title={
              filter === "saved"
                ? "Your saved roads will appear here."
                : "No corridors found."
            }
          >
            {filter === "saved"
              ? "Tap the bookmark beside a corridor to save it on this device."
              : "Try another road name or choose a different filter."}
          </Empty>
        ) : (
          <>
            <div className="desktop-table">
              <table>
                <thead>
                  <tr>
                    <th scope="col">MONITORED CORRIDOR</th>
                    <th scope="col">TRAFFIC TIME</th>
                    <th scope="col">EXTRA DELAY</th>
                    <th scope="col">OBSERVATION</th>
                    <th scope="col">
                      <span className="sr-only">Save</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map(({ road, record }, index) => (
                    <tr key={road.id}>
                      <td>
                        <Link
                          href={`/corridors/?road=${road.id}`}
                          className="road-link"
                        >
                          <span className="road-index">
                            {String(page * 8 + index + 1).padStart(2, "0")}
                          </span>
                          <span>
                            {road.name}
                            <small>
                              {record
                                ? `${minutes(record.distanceKm)} km monitored trip`
                                : "Configured endpoint pair"}
                            </small>
                          </span>
                        </Link>
                      </td>
                      <td>
                        <strong>
                          {record ? minutes(record.trafficMinutes) : "—"}
                        </strong>
                        {record && <span className="unit"> min</span>}
                      </td>
                      <td>
                        <span
                          className={`delay-value ${record && record.delayMinutes > 0 ? "has-delay" : ""}`}
                        >
                          {record ? `+${minutes(record.delayMinutes)}` : "—"}
                          {record && <small> min</small>}
                        </span>
                      </td>
                      <td>
                        <StatusPill record={record} now={data.now} />
                        <small className="table-age">
                          {record
                            ? age(record.timestamp, data.now)
                            : "No validated record"}
                        </small>
                      </td>
                      <td>
                        <SaveButton id={road.id} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mobile-corridor-list">
              {visible.map(({ road, record }) => (
                <div className="mobile-corridor" key={road.id}>
                  <div className="mobile-corridor-top">
                    <Link href={`/corridors/?road=${road.id}`}>
                      {road.name}
                      <ArrowUpRight size={14} />
                    </Link>
                    <SaveButton id={road.id} />
                  </div>
                  <div className="mobile-corridor-bottom">
                    <span>
                      <strong>
                        {record ? minutes(record.trafficMinutes) : "—"}
                      </strong>{" "}
                      min <small>traffic time</small>
                    </span>
                    <StatusPill record={record} now={data.now} />
                  </div>
                </div>
              ))}
            </div>
            <div className="table-pagination">
              <span>
                {page * 8 + 1}–{Math.min((page + 1) * 8, rows.length)} of{" "}
                {rows.length} corridors
              </span>
              <div>
                <button
                  className="icon-button"
                  aria-label="Previous page"
                  disabled={page === 0}
                  onClick={() => setPage((value) => value - 1)}
                >
                  <ChevronLeft size={17} />
                </button>
                <button
                  className="icon-button"
                  aria-label="Next page"
                  disabled={(page + 1) * 8 >= rows.length}
                  onClick={() => setPage((value) => value + 1)}
                >
                  <ChevronRight size={17} />
                </button>
              </div>
            </div>
          </>
        )}
      </section>
      <TrustNote />
    </>
  );
}

export function Corridors() {
  const data = useTraffic(),
    [roadId, choose] = useRoadSelection();
  const road = ROADS.find((item) => item.id === roadId)!,
    record = latest(data.live).find((item) => item.roadId === roadId);
  return (
    <>
      <PageHeading
        eyebrow="ONE CORRIDOR, MORE CONTEXT"
        title="Get to know your route."
        description="Inspect the actual endpoint pair behind each observation."
      />
      <Freshness />
      <div className="detail-toolbar">
        <RoadPicker value={roadId} onChange={choose} />
        <SaveButton id={roadId} />
      </div>
      <section className="panel route-detail">
        <div className="route-detail-top">
          <div>
            <span className="eyebrow small">MONITORED CORRIDOR</span>
            <h2>{road.name}</h2>
          </div>
          <StatusPill record={record} now={data.now} />
        </div>
        <div className="route-detail-grid">
          <div className="trip-reading">
            <span className="reading-label">Estimated travel time</span>
            <div className="large-reading">
              {record ? minutes(record.trafficMinutes) : "—"}
              <span> min</span>
            </div>
            <p>
              {record
                ? `Recorded ${eat(record.timestamp, true)} EAT · ${age(record.timestamp, data.now)}`
                : "There is no validated observation for this corridor yet."}
            </p>
            {record && !isFresh(record, data.now) && (
              <div className="subtle-notice">
                This is a historical snapshot. Current travel time is unknown.
              </div>
            )}
            <div className="paired-readings">
              <div>
                <small>Provider baseline</small>
                <strong>
                  {record ? minutes(record.baselineMinutes) : "—"}{" "}
                  <span>min</span>
                </strong>
              </div>
              <div>
                <small>Additional delay</small>
                <strong className="warm-text">
                  {record ? `+${minutes(record.delayMinutes)}` : "—"}{" "}
                  <span>min</span>
                </strong>
              </div>
              <div>
                <small>Route distance</small>
                <strong>
                  {record ? minutes(record.distanceKm) : "—"} <span>km</span>
                </strong>
              </div>
            </div>
          </div>
          <div className="endpoints-card">
            <span className="eyebrow small">THE MEASURED ENDPOINTS</span>
            <div className="endpoint">
              <i>A</i>
              <div>
                <strong>Start point</strong>
                <span>{road.start}</span>
              </div>
            </div>
            <div className="endpoint-connector" />
            <div className="endpoint">
              <i>B</i>
              <div>
                <strong>End point</strong>
                <span>{road.end}</span>
              </div>
            </div>
            <a
              className="button primary"
              target="_blank"
              rel="noopener noreferrer"
              href={directions(road)}
            >
              Open in Google Maps
              <ExternalLink size={15} />
            </a>
            <p>
              For complete directions and your own starting point, continue in
              Google Maps.
            </p>
          </div>
        </div>
        <div className="route-detail-footer">
          <span>
            <Clock3 size={16} /> Weather context: {record?.weather ?? "Unknown"}
          </span>
          <Link href={`/history/?road=${roadId}`}>
            See this corridor’s history
            <ArrowRight size={16} />
          </Link>
        </div>
      </section>
      <div className="info-grid">
        <div className="panel explanatory">
          <Route size={21} />
          <h3>A corridor isn’t a complete journey.</h3>
          <p>
            These monitored trips have specific endpoints. Some overlap. Adding
            their times would not give a reliable door-to-door arrival time.
          </p>
        </div>
        <div className="panel explanatory">
          <ShieldCheck size={21} />
          <h3>Estimates, with their limits visible.</h3>
          <p>
            Times come from Google Distance Matrix. Weather is context, and
            never multiplies or inflates the travel time.
          </p>
        </div>
      </div>
      <TrustNote />
    </>
  );
}

function HistoryChart({ records }: { records: Observation[] }) {
  if (!records.length) return null;
  const width = 900,
    height = 300,
    left = 54,
    right = 24,
    top = 25,
    bottom = 45;
  const first = Math.min(...records.map((record) => record.timestamp)),
    last = Math.max(...records.map((record) => record.timestamp));
  const maximum =
    Math.max(
      1,
      ...records.flatMap((record) => [
        record.trafficMinutes,
        record.baselineMinutes,
      ]),
    ) * 1.15;
  const x = (stamp: number) =>
    first === last
      ? (width + left - right) / 2
      : left + ((stamp - first) / (last - first)) * (width - left - right);
  const y = (value: number) =>
    height - bottom - (value / maximum) * (height - top - bottom);
  return (
    <div className="history-chart">
      <div className="chart-legend">
        <span>
          <i className="traffic-dot" />
          Traffic estimate
        </span>
        <span>
          <i className="baseline-dot" />
          Provider baseline
        </span>
        <small>Travel time · minutes</small>
      </div>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={`Recorded traffic and baseline travel times for ${records.length} observations. Points show observations, not interpolated forecasts.`}
      >
        {Array.from({ length: 5 }, (_, index) => {
          const value = (maximum * index) / 4;
          return (
            <g key={index}>
              <line
                x1={left}
                x2={width - right}
                y1={y(value)}
                y2={y(value)}
                stroke="#e8ece8"
                strokeDasharray="3 5"
              />
              <text x={left - 12} y={y(value) + 4} textAnchor="end">
                {Math.round(value)}
              </text>
            </g>
          );
        })}
        {records.map((record, index) => (
          <g key={record.timestamp}>
            <circle
              cx={x(record.timestamp)}
              cy={y(record.baselineMinutes)}
              r="5"
              fill="#c0c7c4"
              tabIndex={0}
            >
              <title>
                {eat(record.timestamp, true)} EAT: baseline{" "}
                {minutes(record.baselineMinutes)} min
              </title>
            </circle>
            <circle
              cx={x(record.timestamp)}
              cy={y(record.trafficMinutes)}
              r="6"
              fill="#245c50"
              stroke="white"
              strokeWidth="2"
              tabIndex={0}
            >
              <title>
                {eat(record.timestamp, true)} EAT: traffic{" "}
                {minutes(record.trafficMinutes)} min
              </title>
            </circle>
            {(index === 0 || index === records.length - 1) && (
              <text
                x={x(record.timestamp)}
                y={height - 15}
                textAnchor={
                  first === last ? "middle" : index === 0 ? "start" : "end"
                }
              >
                {eat(record.timestamp, true)}
              </text>
            )}
          </g>
        ))}
      </svg>
      <p>
        Each point is a stored observation. Gaps are not filled with invented
        traffic or predictions.
      </p>
    </div>
  );
}

export function History() {
  const data = useTraffic(),
    [roadId, choose] = useRoadSelection(),
    [windowDays, setWindowDays] = useState("7");
  useEffect(() => {
    void data.loadHistory();
  }, [data.loadHistory]);
  const records = useMemo(
    () =>
      data.history
        .filter(
          (record) =>
            record.roadId === roadId &&
            (windowDays === "all" ||
              record.timestamp >= data.now - Number(windowDays) * 86400000),
        )
        .sort((a, b) => a.timestamp - b.timestamp),
    [data.history, roadId, windowDays, data.now],
  );
  const typical = median(records.map((record) => record.delayMinutes)),
    days = new Set(
      records.map((record) =>
        new Intl.DateTimeFormat("en-CA", {
          timeZone: "Africa/Dar_es_Salaam",
        }).format(record.timestamp),
      ),
    ).size;
  return (
    <>
      <PageHeading
        eyebrow="THE RECORD, NOT A PREDICTION"
        title="Look back. Find the context."
        description="Explore the observations behind a corridor, one timestamp at a time."
        action={
          <Download
            records={records}
            filename={`dar-traffic-${roadId}-history.csv`}
          />
        }
      />
      <div className="history-toolbar">
        <RoadPicker value={roadId} onChange={choose} />
        <label className="select-label">
          <CalendarDays size={16} />
          <select
            aria-label="History period"
            value={windowDays}
            onChange={(event) => setWindowDays(event.target.value)}
          >
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="all">All available records</option>
          </select>
        </label>
      </div>
      {data.historyError && (
        <div className="error-notice" role="alert">
          {data.historyError}
          <button onClick={() => void data.loadHistory(true)}>Try again</button>
        </div>
      )}
      <div className="three-metrics">
        <Metric
          label="Recorded observations"
          value={
            data.historyLoading && !records.length
              ? "—"
              : String(records.length)
          }
          note="For the selected corridor and period"
          icon={Database}
        />
        <Metric
          label="Median extra delay"
          value={typical === null ? "—" : minutes(typical)}
          unit="min"
          note="From recorded observations only"
          icon={Timer}
        />
        <Metric
          label="Observed days"
          value={String(days)}
          note="Calendar days in Tanzania time"
          icon={CalendarDays}
        />
      </div>
      <section className="panel chart-panel">
        <div className="section-heading">
          <div>
            <span className="eyebrow small">RECORDED TRAVEL TIMES</span>
            <h2>{ROADS.find((road) => road.id === roadId)?.name}</h2>
          </div>
          <span className="pill neutral">EAT · UTC+3</span>
        </div>
        {data.historyLoading && !records.length ? (
          <div className="loading-block">
            Loading the recorded observations…
          </div>
        ) : !records.length ? (
          <Empty title="No observations in this period.">
            Choose another corridor or a wider date range. Missing data is not
            the same as zero delay.
          </Empty>
        ) : (
          <>
            <HistoryChart records={records} />
            {days < 7 && (
              <div className="chart-footnote">
                <Info size={16} />
                <p>
                  This sample covers {days} {days === 1 ? "day" : "days"}. It
                  cannot establish a reliable weekly traffic pattern.
                </p>
              </div>
            )}
          </>
        )}
      </section>
      {!!records.length && (
        <section className="panel">
          <div className="section-heading">
            <h2>The underlying observations</h2>
            <span className="caption">Most recent first</span>
          </div>
          <div className="scroll-table">
            <table>
              <thead>
                <tr>
                  <th>RECORDED (EAT)</th>
                  <th>TRAFFIC</th>
                  <th>BASELINE</th>
                  <th>EXTRA DELAY</th>
                  <th>WEATHER</th>
                </tr>
              </thead>
              <tbody>
                {[...records]
                  .reverse()
                  .slice(0, 50)
                  .map((record) => (
                    <tr key={record.timestamp}>
                      <td>{eat(record.timestamp, true)}</td>
                      <td>{minutes(record.trafficMinutes)} min</td>
                      <td>{minutes(record.baselineMinutes)} min</td>
                      <td>+{minutes(record.delayMinutes)} min</td>
                      <td className="weather-cell">{record.weather}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
          {records.length > 50 && (
            <p className="table-limit">
              Showing 50 recent rows. Export the full selected sample with CSV.
            </p>
          )}
        </section>
      )}
      <div className="trust-note">
        <Database size={17} />
        <p>
          History covers up to the last 31 days of stored observations. Older
          observations are deleted after 30 days.
        </p>
      </div>
    </>
  );
}

export function Quality() {
  const data = useTraffic(),
    records = latest(data.live),
    index = new Map(records.map((record) => [record.roadId, record]));
  const fresh = records.filter((record) => isFresh(record, data.now)),
    stale = records.length - fresh.length,
    missing = ROADS.length - records.length;
  return (
    <>
      <PageHeading
        eyebrow="THE FEED, IN PLAIN SIGHT"
        title="Trust starts with context."
        description="See which corridors have recent data, and where we don’t have an answer."
      />
      <Freshness />
      <div className="three-metrics">
        <Metric
          label="Recent observations"
          value={String(fresh.length)}
          unit={`/ ${ROADS.length}`}
          note="Recorded within 90 minutes"
          icon={Radio}
          accent
        />
        <Metric
          label="Stale snapshots"
          value={String(stale)}
          note="Stored, but not current conditions"
          icon={Clock3}
        />
        <Metric
          label="Missing corridors"
          value={String(missing)}
          note="No validated record returned"
          icon={Route}
        />
      </div>
      <section className="panel">
        <div className="section-heading">
          <h2>Corridor coverage</h2>
          <span className="pill neutral">{ROADS.length} endpoint pairs</span>
        </div>
        <div className="coverage-list">
          {ROADS.map((road) => {
            const record = index.get(road.id);
            return (
              <div className="coverage-row" key={road.id}>
                <Link href={`/corridors/?road=${road.id}`}>
                  {road.name}
                  <ArrowUpRight size={13} />
                </Link>
                <span className="coverage-time">
                  {record
                    ? `${eat(record.timestamp, true)} EAT`
                    : "No observation"}
                </span>
                <StatusPill record={record} now={data.now} />
              </div>
            );
          })}
        </div>
      </section>
      <div className="info-grid">
        <section className="panel explanatory">
          <Clock3 size={22} />
          <h3>Collection has a daily window.</h3>
          <p>
            Google Cloud collects every 30 minutes from 06:00 to 22:30 Tanzania
            time. There are no overnight updates. Delivery can be delayed;
            always check the observation time.
          </p>
        </section>
        <section className="panel explanatory">
          <Check size={22} />
          <h3>Invalid records stay out.</h3>
          <p>
            We accept traffic-aware observations with a known source, valid
            timestamps, positive durations and distance, and a consistent delay.
            Future-dated and legacy records are excluded.
          </p>
        </section>
      </div>
    </>
  );
}

export function About() {
  return (
    <>
      <PageHeading
        eyebrow="MADE TO BE UNDERSTOOD"
        title="Useful traffic information. Clear limits."
        description="Dar Traffic brings together recorded estimates for 21 corridors in Dar es Salaam."
      />
      <section className="about-intro">
        <div className="about-symbol">
          <Route size={58} />
        </div>
        <div>
          <span className="eyebrow small">THE IDEA</span>
          <h2>A little more context for the roads we share.</h2>
          <p>
            The city moves differently from one road to the next. This website
            lets you inspect specific corridors, compare their traffic estimates
            with a baseline, and see the observations behind the numbers.
          </p>
          <p>
            It is an observation tool. It doesn’t claim to measure every street,
            predict your next journey, or control traffic signals.
          </p>
        </div>
      </section>
      <div className="section-heading standalone">
        <h2>From a request to a useful reading.</h2>
        <span className="caption">How the data reaches you</span>
      </div>
      <div className="method-grid">
        {[
          [
            "01",
            "Collect",
            "A Google-hosted job requests traffic-aware travel times and route distance for configured endpoints.",
          ],
          [
            "02",
            "Validate",
            "Each record is checked before display. Missing weather stays unknown and never inflates traffic.",
          ],
          [
            "03",
            "Show the context",
            "The latest timestamp, freshness, baseline and sample coverage stay visible alongside the estimate.",
          ],
        ].map(([step, title, text]) => (
          <section className="panel method-card" key={step}>
            <span>{step}</span>
            <h3>{title}</h3>
            <p>{text}</p>
          </section>
        ))}
      </div>
      <section className="panel definitions">
        <div>
          <span className="eyebrow small">READING THE NUMBERS</span>
          <h2>What does “extra delay” mean?</h2>
          <p>
            Extra delay is the traffic estimate minus the provider’s baseline,
            with a minimum of zero. The collector calculates this from seconds
            before rounding durations to minutes.
          </p>
          <div className="formula">
            Extra delay <span>=</span> max(traffic time − baseline, 0)
          </div>
          <p>
            A zero estimate doesn’t prove that a road is empty. Different
            corridors can overlap, and their delays cannot be added to measure
            everyone’s time lost across the city.
          </p>
        </div>
        <div className="definition-note">
          <Info size={21} />
          <h3>Why no city efficiency score?</h3>
          <p>
            A defensible city-wide score would need coverage, vehicle counts and
            a validated method that we don’t currently have. We show the
            underlying estimates instead.
          </p>
        </div>
      </section>
      <div className="info-grid">
        <section className="panel explanatory">
          <Database size={23} />
          <h3>Sources and collection</h3>
          <p>
            Travel estimates: Google Distance Matrix. Weather context:
            Open-Meteo. Collection: Google Cloud Scheduler and Cloud Run. The
            website reads stored observations; refreshing does not start
            collection.
          </p>
          <a
            href="https://github.com/jemmziray-tech/Dar_Traffic_Project"
            target="_blank"
            rel="noopener noreferrer"
          >
            View the project and architecture <ArrowUpRight size={15} />
          </a>
        </section>
        <section className="panel explanatory">
          <ShieldCheck size={23} />
          <h3>Forecasts need more than a label.</h3>
          <p>
            No validated prediction model is published. Google Maps content also
            has restrictions on model training. A future model needs permitted
            data and an evaluation against later observations.
          </p>
          <a
            href="https://cloud.google.com/maps-platform/terms"
            target="_blank"
            rel="noopener noreferrer"
          >
            Google Maps terms <ArrowUpRight size={15} />
          </a>
        </section>
      </div>
      <div className="about-credit">
        <span className="location-dot" />
        Built by John Mziray for Dar es Salaam.
        <Link href="/">
          Explore the corridors <ArrowRight size={15} />
        </Link>
      </div>
    </>
  );
}
