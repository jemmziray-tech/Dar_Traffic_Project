# Dar Traffic website

Next.js static export deployed at https://dartraffic.vercel.app/.

Run `npm ci`, `npm test`, `npm run typecheck`, then `npm run build`. Use `npm run dev` for a local preview.

Overview’s live comparison requests Cloud Run only when a visitor clicks a load or refresh button. The response is held in page memory, with no retained response cache. Travel-time and extra-delay bars use the latest recent reading for each corridor. Missing roads are excluded.

History reads at most 31 daily summaries from `permitted_daily_history` and filters source permission, expiry and the rolling 30-day window. It never reads Google estimates as historical records. Source permissions are enforced by the importer before public writes; Firestore denies client writes and access to private records.

Do not embed service-account credentials or Maps keys. Empty history is expected until a reviewed independent dataset is imported. Google attribution assets are documented in `public/ATTRIBUTION.md`.
