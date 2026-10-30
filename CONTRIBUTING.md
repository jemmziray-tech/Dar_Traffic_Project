# Contributing

Use Python 3.11 or later and install `requirements-dev.txt` in a virtual environment.

Before opening a pull request:

```sh
python -m ruff check .
python -m ruff format --check .
python -m pytest tests/ -v
```

Keep changes focused. Describe the behavior that changed and how it was checked. Comments should explain a decision or a constraint rather than repeat the code.

Provider measurements must remain unchanged by weather or time-of-day assumptions. Keep scenarios separate from observations, and make sample size and freshness visible. Add regression coverage when changing calculations, provider parsing or page behavior. Tests must use fixtures or mocks; they must not make paid Maps requests or write to Firestore.

Keep public page URLs stable. The route registry in `navigation.py` maps the current page names to existing URLs. Small files in `pages/` are Streamlit entry points, not duplicate implementations.

Do not commit credentials, downloaded data, compiled Python files or generated models. Dependency files contain direct requirements for each component; include transitive packages only when the code imports them directly.

The manual collector workflow is a production operation. A code or documentation change should not enable a recurring schedule or run collection as part of CI.
