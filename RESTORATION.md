# Dar Traffic restoration audit — 30 October 2026

## Repository and history

- Reviewed the 138-commit history and all three remote branches.
- Main: d40826e, dated 28 October 2026, explicitly paused collection/retraining and removed tracked data/model artifacts.
- fix/traffic-system-failures: 9ff790a; copilot/cross-check-pipeline-failures: e0824d3. Both are ancestors of main; no unique commits remain on either branch.
- No issues or pull requests were returned by GitHub at audit time.
- Recent scraper runs were skipped, consistent with the unconditional false job condition. An external repository_dispatch source is still triggering the paused job alongside its cron.
- Dashboard remains https://dartrafficproject-johnmziray.streamlit.app/ . Google project selected by owner: dar-traffic (693791183501).

## Findings and repairs

1. Removed synthetic rush-hour/rain multipliers. Live duration, baseline duration, and actual route distance now come directly from the traffic-aware provider response, retaining sub-minute precision.
2. Removed OSRM substitution for traffic measurements. Missing traffic or provider failure now leaves the last observation intact and fails the collection run.
3. Deferred cloud initialization until execution, allowing credential-free regression tests. Added Application Default Credentials support.
4. Live and history writes now share an atomic batch. Schema version and source identify corrected records. Unknown weather no longer silently becomes clear weather.
5. Training excludes legacy synthetic records and unknown weather, waits for sufficient data, and evaluates against a later chronological holdout. Removed automatic deletion of historical records from the training script.
6. Corrected previous_delay versus delay_velocity feature mismatch. Future predictions still assume previous_delay=0 and standard temperature/weather scenarios; these remain estimates requiring evaluation.
7. Dashboard, corridor comparisons, and RL scenario exclude stale (>90 minutes), unverified, and legacy rows. Historical analytics exclude legacy rows. Collection is normally inactive overnight, so the dashboard will correctly show unavailable data then.
8. Corridor comparisons use recorded durations, not the former speed-based arbitrary formula. The configured corridor lists contain overlaps, direction mismatches, and gaps: they are explicitly labelled incomplete corridor comparisons, not verified journey ETAs. A genuine journey planner should query complete origin-to-destination routes.
9. RL tracker is now an adjustable what-if scenario, with no claimed measured 70.1% real-world improvement. RL simulation has no real signal-control connection.
10. Migrated the retired Gemini 2.0 integration to google-genai with configurable GEMINI_MODEL (default gemini-3.8-flash).
11. API input bounds and supported road validation prevent invalid times, duplicate segments, unsupported roads, and unbounded history reads.
12. Unit CI no longer receives production cloud secrets. Added focused regression tests.

## What has not been verified

Live Google API responses, Firestore access, current secret validity, quotas, billing status, the deployed Streamlit environment, and full end-to-end ingestion were not verified. A local mock passing is not proof that production is healthy. No production cloud data was changed. No paid resources were provisioned.

The existing dependencies use broad minimum versions. Python 3.10.0 raised a Google library support warning locally; upgrade deployment/runtime to a supported Python release and generate a tested lockfile before a wider launch. Old checked-in bytecode should be removed in a separate cleanup.

## Controlled restart (requires owner approval)

Keep the existing Streamlit deployment and its repository/main/app.py configuration.

1. Verify that FIREBASE_KEY_JSON points to dar-traffic, and MAPS_API_KEY is valid for the enabled traffic-aware Maps service. Never paste credentials into issues, chat, or tracked files.
2. Check Maps usage/quotas and budget alerts in dar-traffic. The existing 21-road, 34-runs/day cron implies 714 routing elements/day before retries. repository_dispatch can add extra runs and should be disabled or deduplicated before recurring collection.
3. Review Google Maps data display, caching/storage, and model-training rights for the intended use. Existing historical persistence and Pydeck mapping must be assessed against the applicable agreement before public use. Provider terms: https://developers.google.com/maps/documentation/distance-matrix/policies . Distance Matrix is legacy; if unavailable in this project, implement Routes API rather than falling back to synthetic traffic.
4. Merge the reviewed repair branch. Keep both collection and retraining paused initially.
5. Change only the scraper job condition from false to `github.event_name == 'workflow_dispatch'` and add a concurrency group. Trigger one manual run; inspect all 21 successful writes, source/schema, timestamps, and provider timings. Confirm the existing Streamlit dashboard displays those records.
6. Only after that successful run, approve scheduled collection. Retain the current 30-minute schedule unless a different cost/cadence is agreed. Avoid duplicate external dispatches.
7. Leave retraining paused until clean, permitted historical data is sufficient. Repair its commit step to tolerate missing files, set least-privilege contents:write explicitly only if automatic model publishing is approved, and separate synthetic RL training from production traffic forecasting.
8. Set Streamlit GEMINI_API_KEY and optionally GEMINI_MODEL, then test a briefing. The copilot must describe observations as estimates and must not claim verified routing or signal-control outcomes.

## Validation

- Seven focused tests passed locally after the core repairs.
- Python compilation and diff whitespace checks performed.
- All seven Streamlit pages started without exceptions with mocked empty Firestore data. This checks startup/empty states, not real credentials or populated analytics.
- Production deployment and recurring jobs remain pending approval and credential/service validation.

## Verified restoration outcome — 30 October 2026

Following owner approval, PR #1 was merged as 47b6e16198e1dd5f2cd65ba1277846f7864caa88 after GitHub checks passed; main-branch CI also passed. The workflow permits manual collection only, with read-only repository permissions and serialized runs. Recurring triggers and retraining remain paused.

Manual collection [41036391438](https://github.com/jemmziray-tech/Dar_Traffic_Project/actions/runs/41036391438) succeeded at 09:51 UTC / 12:51 EAT. Logs confirm successful weather lookup and Firestore synchronization for all 21 roads. The existing Streamlit dashboard displayed the new observations, and the History page also loaded successfully. Provider access, database writes, deployed code, and dashboard reads are therefore verified for this one run.

Continuous operation, billing/quota configuration, AI briefing responses, predictive model performance, and Maps retention/training permissions remain unverified. Models remain absent pending clean, permitted training data. Without another collection, records will age out of the live display after 90 minutes.
