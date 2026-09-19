# FinGuard

Intelligent Financial Fraud Detection & Transaction Monitoring Platform — a
portfolio-grade analytics project combining Python, SQL, machine learning, and
Power BI.

[![CI](https://github.com/FaizaanMd/FinGuard/actions/workflows/ci.yml/badge.svg)](https://github.com/FaizaanMd/FinGuard/actions/workflows/ci.yml)

> **Status note:** This is a *fraud analytics and transaction monitoring
> prototype* with a reproducible machine learning and reporting workflow. It is
> not a production or regulatory-grade banking security system.

## Project structure

```
FinGuard/
├── data/            # raw + processed datasets (see data/README.md)
├── notebooks/       # EDA, statistical analysis, model evaluation
├── src/             # modular pipeline code (cleaning, features, models)
├── sql/             # schema + analytical queries
├── models/          # serialized models + experiment log
├── tests/           # unit tests
├── dashboard/       # Power BI file + screenshots
└── requirements.txt
```

## Setup

1. Install Python 3.12, PostgreSQL 17, and Git.
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in the PostgreSQL connection details.
4. Obtain the dataset (see `data/README.md`) and place it in `data/raw/`.

## Roadmap

- [x] Phase 1 — Environment & project skeleton
- [x] Phase 2 — Dataset acquisition & validation
- [x] Phase 3 — Cleaning & feature engineering
- [x] Phase 4 — SQL database integration
- [x] Phase 5 — SQL analytics
- [x] Phase 6 — EDA & statistical analysis
- [x] Phase 7 — Rule-based detection
- [x] Phase 8 — Machine learning models
- [x] Phase 9 — Anomaly detection
- [x] Phase 10 — Power BI dashboard (views, exports, and built `.pbix` in `dashboard/`)
- [x] Phase 11 — Testing & quality
- [x] Phase 12 — Documentation & portfolio

## Key results (Track A — ULB credit-card benchmark)

| Detector | Kind | Precision | Recall | PR-AUC | Alerts on test |
|---|---:|---:|---:|---:|---:|
| Rule engine (baseline) | supervised rules | 0.28% | 15.7% | — | 26,632 |
| Logistic Regression | supervised | 78.9% | 78.9% | 0.731 | 95 |
| **Random Forest** | supervised | **93.7%** | 77.9% | **0.847** | **79** |
| Isolation Forest | unsupervised | 21.0% (top-200) | 44.2% | 0.207 | 568 |

Random Forest detects ~78% of fraud with 5 false positives (vs 26k rule
alerts); scores, confusion matrices, and every decision are documented in
`reports/`.

## Reproduce everything

```
.venv\Scripts\activate
pip install -r requirements-dev.txt      # dev tools (pytest, pytest-cov)
python scripts\run_all.py                # 8-stage runbook: data -> DB -> models -> exports
python -m pytest --cov=src               # 53 unit tests, DB-free, ~25 s
```

`run_all.py` validation + cleaning + feature stages run without a database;
stages 4–8 (PostgreSQL, alerts, models, dashboard exports) need the `finguard`
database and `.env`. See `reports/testing/README.md` for the test design and
the bugs the suite caught.

## Report index

| Topic | Location |
|---|---|
| Data dictionary & quality | `data/` |
| SQL analytics (23 queries) | `sql/analytics_summary.md` |
| EDA & statistics | `reports/eda/` |
| Rule baseline | `reports/rules/README.md` |
| Model evaluation | `reports/model_eval/README.md` |
| Anomaly detection | `reports/anomaly/README.md` |
| Power BI build guide | `dashboard/README.md` |
| Tests & coverage | `reports/testing/README.md` |

## Tech stack

Python 3.12 (pandas · NumPy · scikit-learn · SQLAlchemy/psycopg2 · scipy ·
Jupyter) · PostgreSQL 17 · Git · Power BI Desktop · GitHub Actions (CI).