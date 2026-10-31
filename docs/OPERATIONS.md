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

| Website | https://dartraffic.vercel.app/ — Next.js static export on Vercel |

| Old address | Streamlit Community Cloud, `main`, `app.py` — moved notice only |



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



The dashboard reads `live_traffic` and the per-day `daily_history` summaries through Firestore REST. Rules deny client writes and access to all other collections, including the lease, and reject public list queries without a small limit (50 live, 31 days, 100 raw history records). Authorized collector writes use IAM. Editing `firestore.rules` or `firestore.indexes.json` does not deploy them automatically; deploy both with `firebase deploy --only firestore --project dar-traffic`. The History page needs the `daily_history` index (document ID, descending), so deploy rules and indexes before merging website changes that depend on them.

The collector sets `expire_at` 30 days ahead on `traffic_history` and `daily_history` documents (`RETENTION_DAYS` in `scrape_traffic.py`). The `prepare` phase enables Firestore TTL deletion on that field; deletion usually happens within a day of expiry. Confirm the retention period against the current Google Maps Platform terms before raising it. Set a billing budget alert on the project so unexpected read or Maps costs are noticed.



Live and history reads are cached for five minutes. The refresh button fetches the latest stored live observations. It cannot collect traffic or change schedules. Current summaries exclude observations older than 90 minutes. Historical views read at most the 31 newest daily summary documents.



Check Cloud Run executions for `Collection complete: 21/21 roads`, then inspect Data status for freshness and missing corridors. Check Cloud Scheduler's last result separately to verify trigger delivery. A successful trigger means a run was requested, not that collection completed. Review billing and quotas in Google Cloud; the website does not report account health.



The standard [Google Maps terms, section 3.2.3(c)](https://cloud.google.com/maps-platform/terms) prohibit using Maps content to train, test or validate models. A future training pipeline needs suitable rights or a separate modelling dataset and evaluation on later dates. No automatic model training is deployed.



## Website releases



Website source is in `web/`. Its GitHub check installs locked dependencies, runs the data tests and TypeScript checks, then builds the static export. Test a release with real read-only observations before publishing its `out/` directory. Vercel project `dartraffic`, in the `jemmziray-techs-projects` team, builds the repository's `web/` directory with Node.js 24. Its Git integration deploys pushes to `main` and creates previews for other branches. Keep the Next.js output-directory override unset; Vercel detects the static export automatically. The production website is public, while preview deployments retain Vercel authentication.



The Streamlit deployment remains connected to `app.py` on `main` only to serve existing bookmarks. It shows a move notice and link; it no longer queries Firestore. Do not restore a second collection timer or a second dashboard behind that address.

