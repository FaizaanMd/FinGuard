# Phase 10 — Power BI Dashboard

**Final deliverable: `FinGuard_Dashboard.pbix`** — open it with Power BI Desktop.
Three pages: *Monitoring overview*, *Detection performance*, *Alert workload*.
A companion project (`FinGuard.pbip` + `FinGuard.Report/` +
`FinGuard.SemanticModel/`) is also included as the editable source of the same
report.

The `.pbix` was built by hand in Power BI Desktop. If you need to rebuild or
improve it, this guide tells you exactly what to click and which visual to draw
from which data source. Data is ready in two forms:

1. **Live**: PostgreSQL `finguard` database — views `vw_*` (see
   `sql/dashboard_views.sql`). Regenerate with
   `python -m src.dashboard_export` (also refreshes the CSVs below).
2. **Import**: `data/dashboard_export/vw_*.csv`.

## 0. Connect (2 minutes)

1. Open **Power BI Desktop** → **Get Data** → search **PostgreSQL** → Connect.
2. Server `localhost`, Database `finguard`, Data Connectivity mode *DirectQuery*
   or *Import* (Import is fine for this scale).
3. PostgreSQL user `postgres` + password from `FinGuard/.env` (`DB_PASSWORD`).
4. After login, tick all seven `vw_*` views and **Load**.

> If the connector is missing, install the free **Npgsql/PostgreSQL ODBC**
> driver or just **Import** the CSVs from `data/dashboard_export/` (same
> content).

## Page 1 — Monitoring overview (fraud analysts)

Visuals (column/row 1 of `vw_class_overview`, `vw_hourly_analysis`):

| Visual | Data (table) | Setup |
|---|---|---|
| Card | `vw_class_overview` | `txns` (sum) → "Total transactions" |
| Card | `vw_class_overview` | `txns` filtered `class=1` → "Fraud transactions" |
| Card | `vw_class_overview` | `share_pct` filtered `class=1` → "Fraud rate %" |
| Pie/Donut | `vw_class_overview` | Legend `class`, Values `txns` |
| Line chart | `vw_hourly_analysis` | X `hour_bucket`, Y `txns` and `fraud_rate_pct` (second Y axis optional) |

Notes for the report text boxes: fraud rate 0.167%; base rate is the
benchmark; hour axis is a **derived** cycle, not a clock time (state this on
the page).

## Page 2 — Detection performance (model comparison)

Data: `vw_model_test_confusion.csv` + `reports/model_eval/metrics.csv`,
`reports/anomaly/README.md` table.

| Visual | Setup |
|---|---|
| Table | `vw_model_test_confusion`: model_name, precision_pct, recall_pct, f1_pct, tp, fp, fn, tn |
| Clustered column | X model_name, Y precision_pct + recall_pct (two series) |
| Card/Table | Rules `ANY_RULE` 0.28% precision / 15.65% recall from Phase 7 |
| Table | IF: PR-AUC 0.207, ROC-AUC 0.953 (from Phase 9 log) |

Suggested text boxes: “Random Forest is the primary detector — 93.7%
precision at 78% recall on held-out test with only 5 false positives vs 20 for
LR.” All metrics measured on the same test split.

## Page 3 — Alert workload (operations)

Data: `vw_alert_overview`, `vw_alert_risk_buckets`, `vw_transaction_monitoring`.

| Visual | Data | Setup |
|---|---|---|
| Stacked bar | `vw_alert_overview` | Legend `alert_status`, Values `alerts` (axis `alert_source`) |
| Donut | `vw_alert_risk_buckets` | Legend `risk_bucket`, Values `alerts` (slicer `alert_source`) |
| Slicer | `vw_transaction_monitoring` | Field `alert_count` (dropdown) |
| Table | `vw_transaction_monitoring` | transaction_id, amount, class, max_risk_score, alert_sources, rf_probability_test (filter alert_count > 0) |

Text: “Alerts are triage signals, not fraud verdicts. Statuses are simulated
workflow states.”

## 4. Save & screenshot

- Save as `dashboard/FinGuard_Dashboard.pbix`.
- Publish-friendly: export each page as PNG →
  `dashboard/screenshots/page1_monitoring.png`,
  `page2_detection_performance.png`, `page3_alert_workload.png`.

## If anything is missing

`python -m src.dashboard_export` re-applies the views and re-dumps the CSVs
idempotently — it needs the `finguard` database loaded (Phase 4) with alert +
prediction data (Phases 7–9).