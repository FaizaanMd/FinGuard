-- Power BI dashboard views (Track A)
-- Create or replace read-only views Power BI can query via the PostgreSQL
-- connector. Applied by scripts/export_dashboard_data.py (idempotent).
--
-- NOTE: no semicolons inside comments (the loader strips comment lines, then
-- splits on ';').

DROP VIEW IF EXISTS vw_transaction_monitoring;
DROP VIEW IF EXISTS vw_alert_overview;
DROP VIEW IF EXISTS vw_class_overview;
DROP VIEW IF EXISTS vw_hourly_analysis;
DROP VIEW IF EXISTS vw_amount_buckets;
DROP VIEW IF EXISTS vw_model_test_confusion;
DROP VIEW IF EXISTS vw_alert_risk_buckets;

CREATE OR REPLACE VIEW vw_transaction_monitoring AS
-- One row per transaction enriched with alert status and model probability.
SELECT
    t.transaction_id,
    FLOOR(t.transaction_time / 3600.0)::int          AS hour_since_start,
    t.hour_of_day,
    t.day_index,
    t.amount::double precision                       AS amount,
    t.class,
    COALESCE(fa.alert_count, 0)::int                 AS alert_count,
    COALESCE(fa.max_risk, 0)::double precision       AS max_risk_score,
    COALESCE(fa.sources, '')                         AS alert_sources,
    mp.fraud_probability::double precision           AS rf_probability_test
FROM transactions t
LEFT JOIN (
    SELECT transaction_id,
           COUNT(*)            AS alert_count,
           MAX(risk_score)     AS max_risk,
           STRING_AGG(DISTINCT alert_source, ' | '
                      ORDER BY alert_source) AS sources
    FROM fraud_alerts
    GROUP BY transaction_id
) fa USING (transaction_id)
LEFT JOIN (
    SELECT transaction_id, fraud_probability
    FROM model_predictions
    WHERE model_name = 'random_forest' AND split = 'test'
) mp USING (transaction_id);

CREATE OR REPLACE VIEW vw_alert_overview AS
SELECT
    alert_source,
    alert_type,
    alert_status,
    COUNT(*)                                          AS alerts,
    ROUND(AVG(risk_score)::numeric, 3)::double precision AS avg_risk,
    MAX(risk_score)::double precision                  AS max_risk,
    ROUND(100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (), 0), 3)::double precision
                                                       AS share_pct
FROM fraud_alerts
GROUP BY alert_source, alert_type, alert_status
ORDER BY alerts DESC;

CREATE OR REPLACE VIEW vw_class_overview AS
SELECT
    class,
    COUNT(*)                                          AS txns,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 3)::double precision
                                                       AS share_pct,
    SUM(amount)::numeric(18, 2)                        AS total_amount
FROM transactions
GROUP BY class
ORDER BY class;

CREATE OR REPLACE VIEW vw_hourly_analysis AS
SELECT
    FLOOR(hour_of_day)::int                        AS hour_bucket,
    COUNT(*)                                       AS txns,
    SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END)     AS fraud,
    ROUND(100.0 * SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*), 0), 4)::double precision AS fraud_rate_pct
FROM transactions
GROUP BY 1
ORDER BY 1;

CREATE OR REPLACE VIEW vw_amount_buckets AS
SELECT
    CASE
        WHEN amount < 10   THEN '1 <10'
        WHEN amount < 25   THEN '2 10-25'
        WHEN amount < 50   THEN '3 25-50'
        WHEN amount < 100  THEN '4 50-100'
        WHEN amount < 200  THEN '5 100-200'
        ELSE '6 200+'
    END                                                AS bucket,
    COUNT(*)                                          AS txns,
    SUM(class)                                        AS fraud,
    ROUND(100.0 * SUM(class) / NULLIF(COUNT(*), 0), 4)::double precision
                                                       AS fraud_rate_pct
FROM transactions
GROUP BY 1
ORDER BY 1;

CREATE OR REPLACE VIEW vw_model_test_confusion AS
-- Supervised-model confusion on the held-out TEST split.
WITH agg AS (
    SELECT
        mp.model_name,
        COUNT(*)                                            AS test_rows,
        SUM(CASE WHEN mp.predicted_label = 1 AND t.class = 1 THEN 1 ELSE 0 END) AS tp,
        SUM(CASE WHEN mp.predicted_label = 1 AND t.class = 0 THEN 1 ELSE 0 END) AS fp,
        SUM(CASE WHEN mp.predicted_label = 0 AND t.class = 1 THEN 1 ELSE 0 END) AS fn,
        SUM(CASE WHEN mp.predicted_label = 0 AND t.class = 0 THEN 1 ELSE 0 END) AS tn
    FROM model_predictions mp
    JOIN transactions t USING (transaction_id)
    WHERE mp.split = 'test'
    GROUP BY mp.model_name
)
SELECT
    model_name,
    test_rows,
    tp, fp, fn, tn,
    ROUND(100.0 * tp / NULLIF(tp + fp, 0), 2)::double precision AS precision_pct,
    ROUND(100.0 * tp / NULLIF(tp + fn, 0), 2)::double precision AS recall_pct,
    ROUND(100.0 * 2.0 * tp / NULLIF(2.0 * tp + fp + fn, 0), 2)::double precision AS f1_pct
FROM agg
ORDER BY model_name;

CREATE OR REPLACE VIEW vw_alert_risk_buckets AS
SELECT
    alert_source,
    CASE
        WHEN risk_score >= 0.9 THEN '1 high >=0.90'
        WHEN risk_score >= 0.7 THEN '2 medium 0.70-0.89'
        WHEN risk_score >= 0.5 THEN '3 low 0.50-0.69'
        ELSE '4 very-low <0.50'
    END                                              AS risk_bucket,
    COUNT(*)                                         AS alerts
FROM fraud_alerts
GROUP BY alert_source, 2
ORDER BY alert_source, 2;