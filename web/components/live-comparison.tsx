"use client";

import { useState } from "react";
import { ArrowRight, BarChart3 } from "lucide-react";
import Link from "next/link";
import { isFresh, latest, minutes } from "@/lib/traffic";
import { useTraffic } from "./provider";
import { GoogleAttribution } from "./ui";

export function LiveComparison() {
  const data = useTraffic();
  const [measure, setMeasure] = useState<"time" | "delay">("time");
  const records = latest(data.live).filter(record => isFresh(record, data.now));
  const rows = [...records].sort((a, b) =>
    measure === "time" ? b.trafficMinutes - a.trafficMinutes : b.delayMinutes - a.delayMinutes,
  );
  const maximum = Math.max(1, ...rows.map(record =>
    measure === "time" ? record.trafficMinutes : record.delayMinutes,
  ));

  return (
    <section className="panel live-comparison" aria-labelledby="live-comparison-title">
      <div className="section-heading">
        <div>
          <span className="eyebrow small">A SNAPSHOT ACROSS THE CITY</span>
          <h2 id="live-comparison-title">How the corridors compare</h2>
          <p className="caption">Current estimates, in minutes. Routes have different lengths.</p>
        </div>
        <div className="segmented" aria-label="Comparison measure">
          <button aria-pressed={measure === "time"} className={measure === "time" ? "active" : ""} onClick={() => setMeasure("time")}>Travel time</button>
          <button aria-pressed={measure === "delay"} className={measure === "delay" ? "active" : ""} onClick={() => setMeasure("delay")}>Extra delay</button>
        </div>
      </div>
      {rows.length ? (
        <>
          <div className="comparison-scale" aria-hidden="true"><span>0 min</span><span>{minutes(maximum)} min</span></div>
          <ul className="comparison-bars" aria-label={`${measure === "time" ? "Travel time" : "Extra delay"} by corridor`}>
            {rows.map(record => {
              const value = measure === "time" ? record.trafficMinutes : record.delayMinutes;
              return <li key={record.roadId}>
                <Link href={`/corridors/?road=${record.roadId}`} className="comparison-road">{record.name}<ArrowRight size={14} aria-hidden="true" /></Link>
                <div className="comparison-track" aria-hidden="true"><span className={measure === "delay" ? "delay-fill" : ""} style={{ width: `${100 * value / maximum}%` }} /></div>
                <strong>{minutes(value)}<small> min</small></strong>
              </li>;
            })}
          </ul>
          <p className="caption">Showing {rows.length} recently observed corridors. Missing roads are excluded; they are not counted as zero.</p>
          <GoogleAttribution />
        </>
      ) : (
        <div className="comparison-empty">
          <BarChart3 size={36} aria-hidden="true" />
          <h3>{data.loading ? "Requesting current estimates…" : "Compare the roads with a fresh reading"}</h3>
          <p>Load current Google Maps estimates to draw this chart. These readings are kept out of recorded history.</p>
          <button className="comparison-load" disabled={data.loading} onClick={() => void data.refresh()}>{data.loading ? "Loading…" : "Load live comparison"}</button>
          {data.error && <p role="alert">{data.error}</p>}
        </div>
      )}
    </section>
  );
}
