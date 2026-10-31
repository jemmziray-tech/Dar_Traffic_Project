"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  ArrowDownToLine,
  ArrowUpRight,
  Bookmark,
  ChartNoAxesCombined,
  CircleHelp,
  Clock3,
  LayoutGrid,
  MapPin,
  RefreshCw,
  Route,
  ShieldCheck,
} from "lucide-react";
import { useTraffic } from "./provider";
import {
  age,
  csv,
  eat,
  isFresh,
  latest,
  Observation,
  ROADS,
} from "@/lib/traffic";

export const navigation = [
  { href: "/", label: "Overview", icon: LayoutGrid },
  { href: "/corridors/", label: "Corridors", icon: Route },
  { href: "/history/", label: "History", icon: ChartNoAxesCombined },
  { href: "/quality/", label: "Data status", icon: Activity },
  { href: "/about/", label: "About", icon: CircleHelp },
];
export function Brand() {
  return (
    <Link href="/" className="brand" aria-label="Dar Traffic home">
      <img src="/icon.svg" width="37" height="37" alt="" />
      <span>
        dar<span className="brand-light">traffic</span>
        <small>DAR ES SALAAM</small>
      </span>
    </Link>
  );
}
export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname(),
    data = useTraffic();
  const current =
    navigation.find(
      (item) => item.href === pathname || item.href.slice(0, -1) === pathname,
    ) ?? navigation[0];
  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>
      <aside className="sidebar">
        <Brand />
        <div className="nav-label">YOUR CITY, IN VIEW</div>
        <nav aria-label="Main navigation">
          {navigation.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={`nav-item ${current.href === href ? "active" : ""}`}
              aria-current={current.href === href ? "page" : undefined}
            >
              <Icon size={19} />
              <span>{label}</span>
              {current.href === href && <span className="nav-active-dot" />}
            </Link>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="mini-icon">
            <Clock3 size={18} />
          </span>
          <h3>A fresh look, every 30 min.</h3>
          <p>
            Collection runs 06:00–22:30 EAT. Check the observation time before
            you travel.
          </p>
          <Link href="/quality/">
            How fresh is the data? <ArrowUpRight size={14} />
          </Link>
        </div>
        <div className="sidebar-footer">
          <span className="location-dot" />
          Built for Dar es Salaam
          <small>Traffic estimates · not predictions</small>
        </div>
      </aside>
      <div className="main-column">
        <header className="topbar">
          <div className="mobile-brand">
            <Brand />
          </div>
          <div className="breadcrumb">
            Dar es Salaam <span>/</span> <strong>{current.label}</strong>
          </div>
          <div className="topbar-right">
            <span className="time-label">
              <Clock3 size={14} />
              {data.now ? `${eat(data.now)} EAT` : "EAT · UTC+3"}
            </span>
            <button
              className="icon-button refresh-button"
              aria-label="Refresh traffic data"
              title="Refresh stored observations"
              onClick={() => void data.refresh()}
              disabled={data.loading}
            >
              <RefreshCw size={17} className={data.loading ? "spin" : ""} />
            </button>
          </div>
        </header>
        <main id="main-content" tabIndex={-1}>
          {children}
        </main>
        <footer className="page-footer">
          <span>
            Dar Traffic <span className="footer-dot">·</span> A closer look at
            the roads we share.
          </span>
          <Link href="/about/">
            Sources & methodology <ArrowUpRight size={13} />
          </Link>
        </footer>
      </div>
      <nav className="mobile-nav" aria-label="Mobile navigation">
        {navigation.map(({ href, label, icon: Icon }) => (
          <Link
            href={href}
            key={href}
            className={current.href === href ? "active" : ""}
            aria-current={current.href === href ? "page" : undefined}
          >
            <Icon size={20} />
            <span>{label === "Data status" ? "Status" : label}</span>
          </Link>
        ))}
      </nav>
    </div>
  );
}
export function Freshness() {
  const { live, now, loading, error, refresh } = useTraffic(),
    records = latest(live),
    fresh = records.filter((record) => isFresh(record, now));
  const timestamp = records.length
    ? Math.max(...records.map((record) => record.timestamp))
    : null;
  if (loading && !records.length)
    return (
      <div className="feed-status">
        <span className="status-dot muted" />
        Connecting to the traffic feed…
      </div>
    );
  return (
    <div className="freshness-wrap">
      <div className={`feed-status ${fresh.length ? "recent" : "stale"}`}>
        <span className="status-dot" />
        {fresh.length === ROADS.length
          ? "Recent observations"
          : fresh.length
            ? "Partial coverage"
            : "No recent observations"}
        {timestamp && (
          <>
            <span className="separator">/</span>
            <span>
              Recorded {eat(timestamp)} EAT{" "}
              <span className="status-age">· {age(timestamp, now)}</span>
            </span>
          </>
        )}
      </div>
      {error && (
        <div className="error-notice" role="alert">
          {error}
          <button onClick={() => void refresh()}>Try again</button>
        </div>
      )}
      {!loading && !fresh.length && !error && (
        <div className="subtle-notice">
          {timestamp
            ? "The last snapshot is over 90 minutes old. Current conditions are unknown; previous observations are still available."
            : "No validated observations are available yet. We don’t substitute sample traffic."}
          <Link href="/history/">
            View recorded history <ArrowUpRight size={14} />
          </Link>
        </div>
      )}
    </div>
  );
}
export function PageHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">
          <span />
          {eyebrow}
        </div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
export function SaveButton({ id }: { id: string }) {
  const { saved, toggleSaved } = useTraffic();
  const selected = saved.includes(id);
  return (
    <button
      className={`save-button ${selected ? "selected" : ""}`}
      aria-pressed={selected}
      aria-label={`${selected ? "Unsave" : "Save"} ${ROADS.find((road) => road.id === id)?.name ?? "corridor"}`}
      onClick={(event) => {
        event.stopPropagation();
        toggleSaved(id);
      }}
      title={selected ? "Remove from saved corridors" : "Save corridor"}
    >
      <Bookmark size={17} fill={selected ? "currentColor" : "none"} />
    </button>
  );
}
export function Download({
  records,
  filename = "dar-traffic-observations.csv",
}: {
  records: Observation[];
  filename?: string;
}) {
  function download() {
    const url = URL.createObjectURL(
      new Blob([csv(records)], { type: "text/csv;charset=utf-8" }),
    );
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <button
      className="button secondary"
      onClick={download}
      disabled={!records.length}
    >
      <ArrowDownToLine size={16} />
      <span>Export CSV</span>
    </button>
  );
}
export function Empty({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="empty-state">
      <span>
        <Route size={27} />
      </span>
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
export function StatusPill({
  record,
  now,
}: {
  record?: Observation;
  now: number;
}) {
  if (!record) return <span className="pill neutral">Not observed</span>;
  if (!isFresh(record, now))
    return <span className="pill amber">Stale snapshot</span>;
  return (
    <span className={`pill ${record.delayMinutes > 0 ? "amber" : "green"}`}>
      <span className="status-dot" />
      {record.delayMinutes > 0 ? "Added delay" : "At baseline"}
    </span>
  );
}
export function TrustNote() {
  return (
    <div className="trust-note">
      <ShieldCheck size={17} />
      <p>
        Google traffic estimates for monitored endpoint pairs. Coverage is
        limited to these corridors; this is not a city-wide congestion
        measurement.
      </p>
    </div>
  );
}
export function LocationTag() {
  return (
    <span className="location-tag">
      <MapPin size={13} />
      Dar es Salaam, Tanzania
    </span>
  );
}
