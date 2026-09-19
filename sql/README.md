# Database — FinGuard (PostgreSQL)

The `finguard` database stores the processed benchmark transactions plus the
monitored outputs produced by later phases (model scores, alerts).

## Tables

| Table | Purpose | Key columns |
|---|---|---|
| `transactions` | Cleaned + engineered transactions | `transaction_id` PK, `transaction_time`, `v1..v28`, `amount`, `class`, `hour_of_day`, `day_index`, `amount_log` |
| `model_predictions` | Per-(transaction, model) fraud scores | `model_name`, `fraud_probability`, `predicted_label` |
| `fraud_alerts` | Rule/model alerts with risk score | `alert_source`, `risk_score`, `alert_status` (New / Under Review / Escalated / Closed, simulated) |

Constraints: `class IN (0,1)`, `amount >= 0`, `day_index IN (0,1)`, foreign
keys to `transactions.transaction_id`, status whitelist on `fraud_alerts`.

## Schema

`sql/schema.sql` — idempotent DDL (`CREATE TABLE IF NOT EXISTS`), safe to run
via psql or through the loader.

## Loading the data

```powershell
python -m src.db
```

The loader (`src/db.py`) applies the schema, truncates all three tables,
bulk-loads `data/processed/features_engineered.csv`, and verifies the row count
against the source. It requires `.env` with valid `DB_*` credentials.

## Verification

```powershell
psql -h localhost -U postgres -d finguard -f sql/validation_queries.sql
```

or (cross-checks totals from SQL vs the source CSV):

```powershell
python -c "from sqlalchemy import create_engine,text; from src.config import DATABASE_URL, ENGINEERED_FEATURES_PATH; import pandas as pd; e=create_engine(DATABASE_URL); print('DB rows  :', e.connect().execute(text('SELECT COUNT(*) FROM transactions')).scalar_one()); print('CSV rows :', len(pd.read_csv(ENGINEERED_FEATURES_PATH)))"
```