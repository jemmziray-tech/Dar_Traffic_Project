# Dashboard behavior

The public Streamlit app has seven views, all using the same read-only `dar-traffic` data source.

| View | Working capability | Deliberate limit |
| --- | --- | --- |
| Live overview | Freshness and coverage, delay ranking, corridor search, CSV export | Latest observations within 90 minutes; no city efficiency or monetary loss claims |
| Road history | Corridor selector, EAT date range, observed travel-time scatter, CSV | Latest 5,000 history documents; no interpolation or synthetic forecast |
| Patterns & coverage | Sample size, observed days, hourly medians and coverage chart | Missing hours stay missing; short samples have a visible warning |
| Corridor explorer | One configured endpoint pair, estimated times, Google Maps directions link | Does not combine overlapping segments into a claimed complete route |
| Forecast readiness | Fresh-project sample count and historical support by hour | No legacy model is loaded; no predictive accuracy claimed |
| What-if lab | Manual trip inputs or a recent observation; assumed delay reduction slider | Arithmetic scenario, not a measured intervention or trained RL result |
| Data status | All configured corridors, recent/stale/missing state and source limitations | Does not infer a recurring schedule from a successful snapshot |

## Calculations

Only schema 2 Google Distance Matrix observations with traffic explicitly observed, configured road IDs, finite positive durations/distances and valid non-future timestamps are accepted. Stored delay must be non-negative and agree with duration subtraction within rounding tolerance. Collector delay is preserved because it was calculated from provider seconds before durations were rounded to minutes. Speed is derived from stored distance and travel time.

Live summaries use the latest accepted record per corridor within 90 minutes. The sum of delays counts monitored corridors once each and can double-count overlapping geography. It does not represent total person-minutes, daily congestion, network capacity, or economic loss. Zero extra delay means traffic time is no greater than the provider baseline; it does not imply an empty road.

History reads are capped at 5,000 newest documents across the project and cached for five minutes. Live reads are cached for one minute. Refresh clears read caches only. The app has no collection, database-write, model-publication or schedule-control action.

## Verification

Run `python -m pytest tests/ -q`. Tests exercise every view through the main navigation with populated, empty and outage responses; search and scenario interactions; stale/invalid/future/legacy exclusion; collector precision; scenario bounds; observed-hour support; the public reader and collection guards. Browser checks additionally cover real database reads and navigation.

Recurring collection and training remain paused. A model should be evaluated on later held-out dates, compared with simple baselines, and reported with errors in minutes before any forecast UI is enabled. Maps data retention and use terms must be reviewed before expanding storage, training or map integrations.
