# Contributing

Use Node.js 24 for the website in `web/`. Run `npm ci`, `npm test`, `npm run typecheck` and `npm run build` there. For collector changes, use Python 3.11 or later and install `requirements-dev.txt` in a virtual environment.

Before opening a pull request:

```sh
python -m ruff check .
python -m ruff format --check .
python -m pytest tests/ -v
```

Keep changes focused. Describe the behavior that changed and how it was checked. Comments should explain a decision or a constraint rather than repeat the code.

Provider measurements must remain unchanged by weather or time-of-day assumptions. Keep scenarios separate from observations, and make sample size and freshness visible. Add regression coverage when changing calculations, provider parsing or page behavior. Tests must use fixtures or mocks; they must not make paid Maps requests or write to Firestore.

Keep public website URLs stable. `app.py` serves only a compatibility notice for old Streamlit bookmarks; do not reintroduce a second dashboard there.

Do not commit credentials, downloaded data, compiled Python files or generated models. Dependency files contain direct requirements for each component; include transitive packages only when the code imports them directly.

The Google Cloud collector is a production operation. Do not change its approved schedule or run additional collection as part of CI. Changes to collection frequency require agreement on usage and cost.
