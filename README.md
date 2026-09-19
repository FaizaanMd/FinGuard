# FinGuard

Intelligent Financial Fraud Detection & Transaction Monitoring Platform — a
portfolio-grade analytics project combining Python, SQL, machine learning, and
Power BI.

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
- [x] Phase 10 — Power BI dashboard (data prep + guided build)
- [x] Phase 11 — Testing & quality
- [ ] Phase 12 — Documentation & portfolio

Progress: Track A benchmark end-to-end. Rule baseline: 0.28% precision /
15.7% recall. Supervised Random Forest: **93.7% precision / 77.9% recall /
PR-AUC 0.847** on held-out test (details in `reports/model_eval/README.md`).
Unsupervised Isolation Forest: ROC-AUC 0.953 / PR-AUC 0.207 label-free
(details in `reports/anomaly/README.md`).