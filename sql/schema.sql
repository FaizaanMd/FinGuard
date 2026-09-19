-- FinGuard database schema (Track A — benchmark transactions + monitored outputs)
-- PostgreSQL 17. Run against the 'finguard' database:
--   psql -h localhost -U postgres -d finguard -f sql/schema.sql
--
-- NOTE: statements are separated by a semicolon. The SQLAlchemy loader
-- (src/db.py) strips comment lines before splitting, so comments never
-- contain semicolons.

BEGIN;

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id   BIGINT PRIMARY KEY,
    transaction_time DOUBLE PRECISION   NOT NULL,   -- seconds from first txn
    v1               DOUBLE PRECISION,
    v2               DOUBLE PRECISION,
    v3               DOUBLE PRECISION,
    v4               DOUBLE PRECISION,
    v5               DOUBLE PRECISION,
    v6               DOUBLE PRECISION,
    v7               DOUBLE PRECISION,
    v8               DOUBLE PRECISION,
    v9               DOUBLE PRECISION,
    v10              DOUBLE PRECISION,
    v11              DOUBLE PRECISION,
    v12              DOUBLE PRECISION,
    v13              DOUBLE PRECISION,
    v14              DOUBLE PRECISION,
    v15              DOUBLE PRECISION,
    v16              DOUBLE PRECISION,
    v17              DOUBLE PRECISION,
    v18              DOUBLE PRECISION,
    v19              DOUBLE PRECISION,
    v20              DOUBLE PRECISION,
    v21              DOUBLE PRECISION,
    v22              DOUBLE PRECISION,
    v23              DOUBLE PRECISION,
    v24              DOUBLE PRECISION,
    v25              DOUBLE PRECISION,
    v26              DOUBLE PRECISION,
    v27              DOUBLE PRECISION,
    v28              DOUBLE PRECISION,
    amount           NUMERIC(18, 2)     NOT NULL,
    class            SMALLINT           NOT NULL,
    hour_of_day      DOUBLE PRECISION,
    day_index        SMALLINT,
    amount_log       DOUBLE PRECISION,
    CONSTRAINT transactions_class_check      CHECK (class IN (0, 1)),
    CONSTRAINT transactions_amount_check     CHECK (amount >= 0),
    CONSTRAINT transactions_day_index_check  CHECK (day_index IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_transactions_class      ON transactions (class);
CREATE INDEX IF NOT EXISTS idx_transactions_hour       ON transactions (hour_of_day);
CREATE INDEX IF NOT EXISTS idx_transactions_amount     ON transactions (amount);

-- Model score output. One row per (transaction, model, run).
CREATE TABLE IF NOT EXISTS model_predictions (
    prediction_id        BIGSERIAL PRIMARY KEY,
    transaction_id       BIGINT NOT NULL
        REFERENCES transactions (transaction_id) ON DELETE CASCADE,
    model_name           VARCHAR(100) NOT NULL,
    fraud_probability    NUMERIC(10, 8) NOT NULL,
    predicted_label      INTEGER NOT NULL
        CONSTRAINT model_predictions_label_check CHECK (predicted_label IN (0, 1)),
    split                VARCHAR(20) NOT NULL DEFAULT 'full',
    prediction_timestamp TIMESTAMP NOT NULL DEFAULT now()
);

ALTER TABLE model_predictions
    ADD COLUMN IF NOT EXISTS split VARCHAR(20) NOT NULL DEFAULT 'full';

CREATE INDEX IF NOT EXISTS idx_predictions_transaction ON model_predictions (transaction_id);
CREATE INDEX IF NOT EXISTS idx_predictions_model       ON model_predictions (model_name);
CREATE INDEX IF NOT EXISTS idx_predictions_split       ON model_predictions (split);

-- Investigation alerts produced by rules and/or models. 'alert_status' is a
-- simulated workflow state, not a connection to any real institution.
CREATE TABLE IF NOT EXISTS fraud_alerts (
    alert_id       BIGSERIAL PRIMARY KEY,
    transaction_id BIGINT NOT NULL
        REFERENCES transactions (transaction_id) ON DELETE CASCADE,
    alert_source   VARCHAR(50) NOT NULL,          -- e.g. 'rule_high_amount', 'isolation_forest'
    alert_type     VARCHAR(100),
    risk_score     NUMERIC(10, 4) NOT NULL,
    alert_status   VARCHAR(50) NOT NULL DEFAULT 'New'
        CONSTRAINT fraud_alerts_status_check
        CHECK (alert_status IN ('New', 'Under Review', 'Escalated', 'Closed')),
    created_at     TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_alerts_status  ON fraud_alerts (alert_status);
CREATE INDEX IF NOT EXISTS idx_alerts_risk    ON fraud_alerts (risk_score);

COMMIT;