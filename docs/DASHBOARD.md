# Website behavior

The public website is [Dar Traffic](https://dar-traffic.justolm128.chatgpt.site/). It uses the read-only `dar-traffic` Firestore feed.

| View | Capability | Limit |
| --- | --- | --- |
| Overview | Recent coverage, median and largest extra delay, corridor search, saved roads, sorting and CSV export | Current summaries exclude observations older than 90 minutes; no city-wide efficiency or economic-loss score |
| Corridors | Traffic time, provider baseline, endpoint coordinates and a Google Maps directions link | Each reading belongs to one configured endpoint pair, not a complete journey |
| History | Corridor and period selectors, observed travel-time points, underlying records and CSV | Latest 5,000 history documents across all corridors; no interpolation or forecast |
| Data status | Recent, stale and missing corridors, timestamps and collection window | A stored snapshot does not prove that the scheduler is healthy |
| About | Sources, calculations, coverage limits and model requirements | No validated prediction model is published |

## Data handling

Only schema 2 Google Distance Matrix observations with traffic explicitly observed, configured road IDs, finite positive durations and distance, and valid non-future timestamps are accepted. Stored delay must be non-negative and consistent with duration subtraction within rounding tolerance. Collector delay is preserved because it is calculated from provider seconds before durations are rounded to minutes. Missing weather stays unknown and does not change travel time.

Extra delay is `max(traffic time - baseline, 0)`. Zero does not prove a road is empty. Corridors can overlap, so their delays cannot measure total person-minutes or congestion across the whole city.

Live reads are cached for one minute and history for five minutes. The website refreshes stored live observations each minute while visible. Refresh never starts a paid Maps request. Saved roads stay in the visitor's browser; no account is required. CSV exports contain the selected records with UTC timestamps; on-screen observation times use Tanzania time.

## Verification

From `web/`, run `npm test`, `npm run typecheck` and `npm run build`. Browser verification covers real reads, navigation, search, saved roads, pagination, CSV downloads and desktop/phone layouts. Collector tests remain in the root `tests/` directory and must not contact paid APIs or write to production Firestore.

Collection runs every 30 minutes from 06:00 to 22:30 EAT. There is no automatic training pipeline. A future model needs permitted data, evaluation on later held-out dates and published errors before a prediction interface is added.

## Old Streamlit address

The former Streamlit screens have been retired. `app.py` shows a moved notice with a link to the website, including the named routes used by old bookmarks. The previous implementation is available in Git history.
