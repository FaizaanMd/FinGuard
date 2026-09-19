# Phase 8 — Model Evaluation (Track A)

Sources: `src/fraud_detection.py`, `src/model_evaluation.py`,
`scripts/train_and_evaluate.py` (reproduces everything with `python
scripts/train_and_evaluate.py`).

## Protocol (leakage-safe)

1. Stratified split: **train 60% / validation 20% / test 20%** (fraud 284/94/95).
2. All preprocessing (`StandardScaler`) is fit on **train only**, inside a
   `Pipeline` — no test/validation statistics observed during fitting.
3. F1-optimal decision threshold is chosen on **validation only**.
4. Every number below is measured on the **held-out test split** at that
   threshold. Nothing is tuned on test.

## Results (test split, 56,746 txns incl. 95 fraud)

| Model | Threshold | Precision | Recall | F1 | PR-AUC | ROC-AUC | Alerts | FP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Logistic Regression | 0.9999 | 0.789 | 0.789 | 0.789 | 0.731 | 0.962 | 95 | 20 |
| **Random Forest** | 0.381 | **0.937** | 0.779 | **0.851** | **0.847** | 0.960 | 79 | **5** |

Random Forest is the better detector: nearly the same recall (78% vs 79%) with
**4x fewer false positives** (5 vs 20) and higher PR-AUC. Confusion matrices:

| Model | TN | FP | FN | TP |
|---|---:|---:|---:|---:|
| Logistic Regression | 56,631 | 20 | 20 | 75 |
| Random Forest | 56,646 | 5 | 21 | 74 |

## Note on the LR threshold (calibration artifact)

With `class_weight="balanced"`, LR probabilities saturate toward extremes; the
F1-optimal threshold lands at the **top edge of the grid (0.9999)**. The test
metrics at that threshold are still valid (threshold tuning on validation is a
legitimate procedure) but the choice is fragile — a documented limitation, and
the reason RF is recommended as the primary model.

## Contrast with Phase 7 rules

| Detector | Precision | Recall | Alert rate |
|---|---:|---:|---:|
| Rules (ANY_RULE) | 0.28% | 15.7% | 9.4% |
| Logistic Regression | 78.9% | 78.9% | 0.17% |
| Random Forest | 93.7% | 77.9% | 0.14% |

The rules-only baseline flags ~26k transactions for 16% recall; RF flags **79**
transactions for 78% recall. This is the headline result that motivates the
model-based pipeline.

## Artefacts

- `reports/model_eval/pr_curves.png` — PR curves, both models (test)
- `reports/model_eval/threshold_sweeps.png` — validation threshold sweeps
- `reports/model_eval/confusion_matrices.png` — test confusion matrices
- `reports/model_eval/metrics.csv`, `confusion.csv`
- `models/logistic_regression.joblib`, `models/random_forest.joblib`
- `models/experiments.csv` — append-only experiment log (cleaned to final run)
- `model_predictions` table (113,492 rows, `split='test'`)

## Data notes

- Features: `V1..V28`, `amount_log`, `hour_of_day`, `day_index`. Raw `Time`
  and raw `Amount` are deliberately excluded (documented in `src/config.py`).
- Coefficients/importances are omitted from the headline tables on purpose:
  `V1..V28` are anonymous PCA components, so "top features" carry no business
  meaning here.