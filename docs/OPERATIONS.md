# Operating Dar Traffic

## Services

- Google Cloud project: `dar-traffic` (project number `693791183501`).
- Firestore database: `(default)`, located in `africa-south1`.
- Collections: `live_traffic` and `traffic_history`.
- Website: Streamlit Community Cloud, repository `main`, entry point `app.py`.
- Traffic provider: Google Distance Matrix. Weather context: [Open-Meteo](https://open-meteo.com/en/docs).

The old `dar-traffic-command` Firebase project is not used by the current application. No data is copied from it.

## Collector

The `Collect traffic` workflow in `.github/workflows/traffic_scraper.yml` has a manual trigger only. Running it makes billable Maps requests and writes observations. Do not use a workflow run as a routine health check.

GitHub Actions authenticates through Workload Identity Federation:

- Pool: `dar-traffic-github`; provider: `github`.
- Service account: `dar-traffic-collector@dar-traffic.iam.gserviceaccount.com`.
- Google Cloud project is explicit in the collector; ambient project settings do not change the destination.
- The repository secret `MAPS_API_KEY` supplies the Maps credential. No Firebase JSON key is needed.

The provider trust is restricted to this repository, `main`, and the collector workflow. The service account has Firestore data access; the matching repository identity has permission to impersonate that account. Changing the workflow path requires reviewing the provider trust condition.

A run collects each configured corridor with up to five concurrent workers. Every successful corridor is written to the live and history collections in one batch. A failed corridor retains its previous live record. The workflow exits unsuccessfully if any corridor failed, even if others succeeded. Weather failure does not fabricate weather and does not stop valid traffic collection.

For local collector development, install `scraper_requirements.txt` and use your normal Google Cloud Application Default Credentials plus the `MAPS_API_KEY` environment variable. Running `python scrape_traffic.py` performs a real collection; importing the module does not initialize clients or collect data.

## Website and access

The dashboard reads Firestore through an unauthenticated REST client restricted in code to the two traffic collections. The deployed rules allow public reads of those records and deny client writes and other collection access. Authorized collector writes use IAM independently of client rules. The rule source is `firestore.rules`; changing this file alone does not deploy the rules.

Public reads can incur Firestore charges. Live reads are cached for one minute and history reads for five minutes. Refresh clears read caches only. It cannot call Maps, write observations or alter collection schedules.

To deploy code, merge tested changes to `main`. Keep Streamlit configured to `app.py`; use Python 3.11 or later for a new deployment. No dashboard secret is required. If old Firebase or Gemini secrets remain in Streamlit, the current application does not read them.

## Routine checks

1. Check the latest collector run for `Collection complete: 21/21 roads` and a successful result.
2. Inspect **Data status** for recent, stale and missing corridors. A successful run does not imply that a schedule is enabled.
3. Compare the observation timestamp with the intended collection time. Public pages use EAT (UTC+3); storage timestamps are UTC.
4. Review Maps usage, Firestore reads and billing in Google Cloud separately. The dashboard does not report quotas or account health.

If the database cannot be reached, the app shows an unavailable state. If observations are older than 90 minutes, current summaries are withheld; historical views still work. Do not substitute fabricated observations to hide these states.

## Future work

Before enabling recurring collection, decide its cadence and budget and review provider retention and use requirements. Before adding forecasts, collect an appropriate history, evaluate on later dates against simple baselines, and publish error in minutes with coverage. Earlier training scripts and simulations were removed from the active tree because they do not meet the fresh-project contract; they remain in Git history.
