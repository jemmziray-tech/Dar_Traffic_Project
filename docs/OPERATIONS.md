# Operating Dar Traffic

## Services

Google Cloud project: `dar-traffic` (`693791183501`).

| Resource | Name / location |
| --- | --- |
| Cloud Run Job | `dar-traffic-collector`, `africa-south1` (Johannesburg) |
| Cloud Scheduler | `dar-traffic-collector`, `europe-west1` |
| Container registry | `africa-south1-docker.pkg.dev/dar-traffic/dar-traffic/collector` |
| Cloud Build source bucket | `dar-traffic-build-source-693791183501` |
| Maps credential | Secret Manager secret `dar-traffic-maps-api-key` |
| Firestore database | `(default)`, `africa-south1` |
| Website | Streamlit Community Cloud, `main`, entry point `app.py` |

Cloud Scheduler uses `0,30 6-22 * * *` in `Africa/Dar_es_Salaam`: 34 runs per day, from 06:00 through 22:30 EAT. At 21 corridors this is 714 routing elements/day before provider retries. Google schedules are not a hard real-time guarantee. GitHub Actions runs tests only, not collection.

The scheduler's region is separate from the job's region: it makes an authenticated API request, while the collector container and Firestore run in Johannesburg. The old `dar-traffic-command` database is not used.

## Identities and credentials

- `dar-traffic-collector@dar-traffic.iam.gserviceaccount.com`: existing Firestore data access, plus Secret Accessor on the Maps secret only.
- `dar-traffic-scheduler@dar-traffic.iam.gserviceaccount.com`: Cloud Run Invoker on this job only. No Firestore or secret access.
- `dar-traffic-build@dar-traffic.iam.gserviceaccount.com`: writer on the container repository, reader on the source bucket, and project logging/service-usage permissions. No traffic data or Maps secret access.

The dedicated Maps key is restricted to the Distance Matrix API and stored in Secret Manager. There are no service-account JSON keys. GitHub federation is retired from collection. Never put credentials in the repository or copy secret values into logs.

## Deploying a collector change

Use Google Cloud CLI with an authorized project administrator account. Run the tests and style checks before releasing. From the repository root:

```sh
python scripts/deploy_collector.py prepare
python scripts/deploy_collector.py build
```

`prepare` enables the required APIs and creates or reuses the named resources and scoped permissions. `build` uploads only an explicit allowlist of collector source files and prints the Cloud Build ID and content-tagged image. It does not upload local configuration or credentials.

Wait for the build to succeed, then deploy the image:

```sh
python scripts/deploy_collector.py deploy
```

Deployment does not start collection or enable a new scheduler. A manual test is a production operation that can make billable Maps requests:

```sh
gcloud run jobs execute dar-traffic-collector --project=dar-traffic --region=africa-south1 --wait
```

After the job is verified, create or update its schedule:

```sh
python scripts/deploy_collector.py schedule
```

Do not add a GitHub collection timer. Additional manual runs and changes to the cadence alter usage and charges. Cloud Run, Scheduler, builds, container storage, Secret Manager, Maps and Firestore have separate usage charges.

## Execution behavior

The job has one task, 1 CPU, 512 MiB memory, an eight-minute timeout and no task retries. The scheduler has no automatic retry attempts. A private `_collector_state/collection` record uses a Firestore transaction to prevent overlapping runs and a second collection in the same UTC half-hour slot. A ten-minute lease expires after a crashed or timed-out container. A repeated invocation in the same slot exits without contacting providers, including after a partial failure; the next scheduled slot can collect again.

Each successful corridor is written to `live_traffic` and `traffic_history` in one batch. Failures retain the previous live record and make the job fail if any corridor failed. Missing or mismatched weather stays unknown and does not alter traffic estimates.

To pause collection:

```sh
gcloud scheduler jobs pause dar-traffic-collector --location=europe-west1 --project=dar-traffic
```

Resume with `gcloud scheduler jobs resume` using the same arguments. Pausing the timer does not cancel an already-started Cloud Run execution.

## Website and monitoring

The dashboard reads the two public traffic collections through Firestore REST. Rules deny client writes and access to all other collections, including the lease. Authorized collector writes use IAM. Editing `firestore.rules` does not deploy it automatically.

Live reads are cached for one minute and history for five minutes. Refresh clears read caches; it cannot collect traffic or change schedules. Current summaries exclude observations older than 90 minutes. Historical views read at most the 5,000 newest records.

Check Cloud Run executions for `Collection complete: 21/21 roads`, then inspect Data status for freshness and missing corridors. Check Cloud Scheduler's last result separately to verify trigger delivery. A successful trigger means a run was requested, not that collection completed. Review billing and quotas in Google Cloud; the website does not report account health.

The standard [Google Maps terms, section 3.2.3(c)](https://cloud.google.com/maps-platform/terms) prohibit using Maps content to train, test or validate models. A future training pipeline needs suitable rights or a separate modelling dataset and evaluation on later dates. No automatic model training is deployed.
