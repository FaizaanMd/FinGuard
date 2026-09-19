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

- [ ] Phase 1 — Environment & project skeleton
- [ ] Phase 2 — Dataset acquisition & validation
- [ ] Phase 3 — Cleaning & feature engineering
- [ ] Phase 4 — SQL database integration
- [ ] Phase 5 — SQL analytics
- [ ] Phase 6 — EDA & statistical analysis
- [ ] Phase 7 — Rule-based detection
- [ ] Phase 8 — Machine learning models
- [ ] Phase 9 — Anomaly detection
- [ ] Phase 10 — Power BI dashboard
- [ ] Phase 11 — Testing & quality
- [ ] Phase 12 — Documentation & portfolio

*(Detailed documentation will be added as each phase completes.)*