# Operations

The public website is https://dartraffic.vercel.app/. Google Cloud project: `dar-traffic` (693791183501).

## Live service

`dar-traffic-live` runs in `africa-south1` using the existing collector service account and Maps key from Secret Manager. `GET /health` checks service health without requesting Maps data. `GET /live` reserves the shared daily allowance, requests the 21 corridors and returns validated estimates without saving their content.

The old `dar-traffic-collector` Scheduler entry in `europe-west1` is paused. Do not resume or manually execute the retired writer; its old container stores Google traffic history.

Release using an authorized Cloud SDK identity:

```sh
python scripts/deploy_live.py build
# Wait for the returned Cloud Build ID to succeed.
python scripts/deploy_live.py deploy
python scripts/deploy_live.py retention
```

The source upload is an explicit six-file allowlist. Confirm the returned service URL matches `LIVE_API_URL` in `web/lib/traffic.ts`. Build and runtime identities have separate roles. No downloaded service-account key is required.

## Database boundaries

Only `permitted_daily_history` is public, with list requests limited to 31 documents. Client writes are denied. `permitted_observations` and `_live_usage` remain private. Run `python scripts/deploy_data_policy.py` to publish `firestore.rules` with an existing Cloud SDK login. Deploy the index/TTL configuration through Firestore administration.

Enable `expire_at` TTL on the three new collections. TTL removes expired storage asynchronously; application reads enforce expiry immediately. Usage counters contain counts, a next-request time and expiry, not route estimates or visitor identifiers.

## Checks before release

Run Python tests and Ruff, then website tests, type checking and the production build. Verify health first. A live smoke test makes billable Maps requests, so use a single explicit request, check the chart values and avoid repeated calls. Confirm history has a clear empty state if no independent source has been imported. Do not load demonstration records into production to fill charts.

The live service allows 714 routing elements per Tanzania day and one request per minute globally. Retries are disabled. This bounds this service’s Maps calls; it is not a project-wide billing cap. Review Cloud billing and alerts independently.
