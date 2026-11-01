# Adding independent observations

`data_sources.json` starts empty. Adding a source is a review decision: check who collected it, whether it derives from Google Maps, and what its written permission allows. A declaration in this file does not grant rights by itself.

A source must be enabled, have kind `own_measurements` or `licensed_dataset`, explicitly declare `derived_from_google_maps: false`, include a nonempty `rights_reference`, and permit `history`. Retention must be 1–365 days. Public display and training are separate permissions (`public_display` and `training`). See `permitted_data.py` for the accepted registry fields.

Supply a JSON array of aggregated corridor observations with a stable `observation_id`, configured `road_id`, timezone-aware `timestamp`, positive `travel_minutes` and `distance_km`. `baseline_minutes` is optional. Driver identifiers and raw GPS traces are not accepted. Do not label Google-derived estimates as independent measurements.

```sh
python scripts/import_observations.py observations.json --source YOUR_REVIEWED_SOURCE
```

The default is validation only. Read the command’s `--help` for input arguments before applying an import. `--apply` requires an authorized Google Cloud identity. Stable source and observation IDs make repeated imports idempotent. An import accepts at most 400 observations. Public daily summaries are bounded to 1,000 observations and 700 KB, and only include records with public-display permission.

Public history covers up to 30 days. Its expiry is fixed from the Tanzania calendar date, with earlier source expiry respected. Private records follow their approved retention. Firestore TTL deletion is asynchronous; readers and exports independently exclude expired records.

The training exporter reads private permitted observations and checks both the stored permission and the currently enabled registry. Removing training permission blocks future exports. Already downloaded files must be managed separately. It refuses to create a training file when there are no eligible records. No model is trained by this importer or exporter.
