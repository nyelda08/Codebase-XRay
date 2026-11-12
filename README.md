# CODEBASE X-RAY

CODEBASE X-RAY is a local, read-only Python application for exploring source repositories through a dark interactive dashboard. It inventories source files, estimates code/comment/blank line counts, parses common dependency declarations, and surfaces lightweight code quality findings. It never executes repository code or installs project dependencies.

## Features

- Language and file inventory, repository size, line statistics, deepest directories, and largest files
- Interactive language, directory, code composition, and file size charts
- Expandable directory explorer and internal Python import relationships
- Dependency parsing for `requirements.txt`, `pyproject.toml`, `Pipfile`, and `package.json`
- TODO/FIXME, large and empty file, duplicate hash, and Python syntax checks
- JSON, file-level CSV, and Markdown report downloads
- Public GitHub repository scanning for hosted deployments
- Excludes `.git`, virtual environments, build outputs, `node_modules`, `.next`, and `.env*` directories by default

## Technology

Python 3.11+, Streamlit, Plotly, and Python standard library modules (`pathlib`, `os`, `ast`, `tomllib`, `hashlib`). GitPython is not required; Git metadata is not currently displayed.

## Install

From this directory, create a virtual environment and install the UI dependencies:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On systems where the Python launcher is unavailable, use `python -m venv .venv` instead.

## Run

```powershell
streamlit run app.py
```

Choose a public GitHub URL or a local directory in the sidebar and select **Scan repository**. The scanner reads files only; it never executes repository code. It skips binary files and files larger than 1 MB, and gracefully ignores inaccessible local files.

## Publish a public demo for free

The app can be deployed on [Streamlit Community Cloud](https://share.streamlit.io/). Push this project to a GitHub repository, then create an app in Community Cloud using `app.py` as the entrypoint. The hosted app defaults to scanning public GitHub repositories by URL; it cannot inspect a visitor's computer because the code runs on the hosting server. Local-folder scanning remains available when running the app on your own machine. GitHub source archives are fetched temporarily, are never executed, and are limited to 30 MB compressed, 100 MB of declared source, and 5,000 archive entries.

For a public LinkedIn demo, use a public GitHub repository for the app and choose a public app visibility setting in Community Cloud. Do not commit `.venv`, credentials, or private source files.

## Project structure

```text
Codebase-XRay/
├── app.py             # Streamlit dashboard and navigation
├── scanner.py         # Read-only traversal and file statistics
├── analyzer.py        # Dependency parsing and lightweight findings
├── visualizations.py  # Plotly charts
├── exporters.py       # JSON, CSV, and Markdown exports
├── requirements.txt
└── README.md
```

## Notes

Line classifications use simple per-language comment-prefix rules, so they are useful estimates rather than compiler-grade metrics. Dependency results reflect declarations discovered in scanned files. Checks are informational and do not amount to a comprehensive security audit. No repository file is modified or run.
