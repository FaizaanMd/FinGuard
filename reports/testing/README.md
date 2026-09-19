# Phase 11 — Testing & Quality (Track A)

## Running the suite

```
.venv\Scripts\activate
python -m pytest                          # fast, database-free
python -m pytest --cov=src --cov-report=term-missing
```

Dev dependencies live in `requirements-dev.txt` (pytest, pytest-cov). Runtime
deps are in `requirements.txt`.

## Design

Tests are **database-free and data-free**: every test builds its own synthetic
frame (see `tests/helpers.py`) that mirrors the benchmark schema, including a
real class signal in `V14`/`V4` so model tests learn something real. This keeps
the suite fast (~24 s) and portable — no PostgreSQL or 62 MB CSV required.

| File | Covers |
|---|---|
| `test_config.py` | feature-vector shape, DB URL, directories |
| `test_data_validation.py` | every quality check PASS/WARN/FAIL |
| `test_data_cleaning.py` | dedup + fraud impact, ids, idempotence |
| `test_feature_engineering.py` | time wrap-around, log1p amount |
| `test_rule_engine.py` | rule construction, probabilistic-OR risk, alert schema |
| `test_fraud_detection.py` | split proportions, stratification, scaler-fit-on-train, threshold tuning |
| `test_model_evaluation.py` | confusion row arithmetic |
| `test_anomaly_detection.py` | risk normalization direction, top-k, sweep monotonicity |
| `test_eda.py` | Cohen's d ranking, imbalance, amount stats, MWU tests |

## Bugs these tests caught during development

1. **Inverted anomaly risk mapping** — a sign error made Isolation Forest scores
   anti-correlated with the label (ROC-AUC ~0.05). A `test_clear_outlier_gets_high_risk`
   regression test now pins the direction.
2. **Split inversion** — the train/validation/test pipeline initially produced
   20/60/20 instead of 60/20/20. `test_split_proportions_follow_config`
   catches it.
3. **`n_rules` counted "any" not "count"** — `score_transactions` reported 1 for
   both single- and multi-rule transactions. Fixed and pinned by
   `test_score_transactions_probabilistic_or`.
4. **`CREATE OR REPLACE VIEW` column renames** — surfaced when exporting
   dashboard views (not unit-testable without a DB; documented in Phase 10).

DB/CLI entry points (`src/db.py`, `src/dashboard_export.py`,
`src/anomaly_eval_plots.py`, plot functions) are exercised live during their
phases rather than in unit tests; the unit layer focuses on pure logic.

## Coverage (pure-logic modules)

| Module | Coverage |
|---|---:|
| `config.py` | 100% |
| `model_evaluation.py` | 98% |
| `rule_engine.py` | 89% |
| `data_validation.py` | 73% |
| `data_cleaning.py` | 67% |
| `feature_engineering.py` | 60% |

HTML report (regenerated per run): `reports/coverage_html/` (git-ignored).