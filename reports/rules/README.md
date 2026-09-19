# Rule-Based Detection — FinGuard Track A

Module: `src/rule_engine.py` · Run: `python -m src.rule_engine`

## Rules

| Rule | Condition | Risk indicator | Weight |
|---|---|---|---|
| `rule_high_value` | amount > data-derived 99th pct (≈ 1,018.06) | Medium | 0.70 |
| `rule_high_value_rapid` | gap to previous txn ≤ 1 s **and** amount > 90th pct (≈ 203.38) | High | 0.85 |
| `rule_night_high_value` | amount > 95th pct **and** hour_of_day < 6 | Medium | 0.55 |

Per-transaction combined risk = probabilistic OR: `1 − Π(1 − w_i)` over
triggered rules.

## Evaluation (vs labels on the benchmark)

| Rule | Alerts | Fraud alerted | Precision | Recall | Alert rate |
|---|---:|---:|---:|---:|---:|
| rule_high_value | 2,838 | 9 | 0.32% | 1.90% | 1.00% |
| rule_high_value_rapid | 26,178 | 69 | 0.26% | 14.59% | 9.23% |
| rule_night_high_value | 744 | 8 | 1.08% | 1.69% | 0.26% |
| **ANY_RULE** | 26,632 | 74 | 0.28% | **15.65%** | 9.39% |

## Interpretation

- Rules detect roughly **16% of fraud by alerting under 10% of transactions** —
  a meaningful baseline but a poor detection ceiling.
- **Lesson learned:** a bare `gap ≤ 1 s` rule triggered on **91%** of the
  dataset (this benchmark is dense, ~1-second-apart traffic). It was therefore
  combined with an amount condition instead of being dropped silently — the
  recalibration is documented, not hidden.
- The anonymized V-features separate classes far better than any amount rule
  (EDA Phase 6), motivating the supervised models in Phase 8.

## Outputs

- `data/processed/alerts_rules.csv` — long-format alerts (matches
  `fraud_alerts` schema)
- `data/processed/transaction_risk.csv` — one row per transaction with
  `risk_score`, `rules_triggered`, `n_rules`
- `fraud_alerts` table in PostgreSQL (idempotent load) — powers the alert
  queries and dashboard

## Caveats

- A rule trigger is a **risk indicator, not a fraud verdict**; statuses like
  "New" are simulated workflow states.
- Thresholds above are data-derived/calibrated for *this* dataset and are
  explicitly labeled; they are not claimed to generalize.