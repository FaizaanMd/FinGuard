# Phase 9 — Unsupervised Anomaly Detection (Track A)

Module: `src/anomaly_detection.py` · Plots: `python -m src.anomaly_eval_plots`

## Method

Isolation Forest, an unsupervised outlier method — **no labels used anywhere in
the pipeline**:
- Fit on the train-only partition (226,980 rows), same split geography as
  Phase 8 so all metrics are directly comparable.
- `contamination = 0.002` is an explicit prior (0.2%). The true fraud rate is
  **never** used to set it — tuning contamination against `Class` would leak
  labels into an unsupervised method.
- Anomaly score = `score_samples` (lower = more anomalous), rescaled to a
  0–1 `risk_score`.

## Results (held-out test, 56,746 rows, 95 fraud)

| Detector | Metric basis | Precision | Recall | PR-AUC | ROC-AUC |
|---|---:|---|---:|---:|---:|
| Isolation Forest (top-200) | unsupervised | 21.0% | 44.2% | 0.207 | 0.953 |
| Isolation Forest (top-50) | unsupervised | 40.0% | 21.1% | 0.207 | 0.953 |
| Random Forest (Phase 8) | supervised | 93.7% | 77.9% | 0.847 | 0.960 |

Isolation Forest is remarkably good for a **label-free** model (ROC-AUC 0.953)
but much weaker at the fraud-relevant precision-recall operating point than the
supervised RF: it flags 200 rows to catch 44% of fraud at 21% precision, while
RF catches 78% of fraud with only 79 alerts.

## Detector overlap (test fraud rows)

| Category | Rows |
|---|---:|
| Caught by IF only | 3 |
| Caught by RF only | 35 |
| Caught by both | 39 |

RF dominates; IF uniquely surfaces 3 additional fraud rows — a small but real
argument for keeping an unsupervised guard in monitoring (labels are scarce in
practice; an unsupervised scorer can detect drift/new fraud families).

## Outputs

- `models/isolation_forest.joblib`
- `data/processed/anomaly_scores.csv` (all transactions, `risk_score` 0–1)
- `data/processed/alerts_anomaly.csv` — 568 alerts (≈ 0.2% of transactions)
- `fraud_alerts` rows with `alert_source = 'isolation_forest'` (idempotent
  replace on re-run)
- `models/experiments_anomaly.csv` — append-only run log
- `reports/anomaly/if_pr_roc.png`, `if_risk_distribution.png`,
  `detector_overlap.csv`

## Caveats

- Anomaly ≠ fraud. Top anomaly scores include legitimate outliers; the
  `risk_score` is a triage signal for human review, not a verdict.
- The `0.2%` contamination prior is data-set-agnostic by design but would need
  recalibration per institution.