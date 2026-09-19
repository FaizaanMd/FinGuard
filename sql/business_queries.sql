-- ============================================================================
-- FinGuard — business-oriented analytics & investigation queries (Track A)
-- Target: PostgreSQL 17, database: finguard
-- Run:   psql -h localhost -U postgres -d finguard -f sql/business_queries.sql
--
-- These queries model the *monitoring workflow*: produce alerts, prioritize
-- them, and narrow candidate lists for analyst review. They show how rules and
-- threshold decisions translate into an alert workload.
--
-- A trigger here is a risk indicator, not a fraud verdict.
-- Queries on model_predictions / fraud_alerts run now but return zero rows
-- until Phase 8 populates those tables.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. Baseline high-value rule: flag amount > 99th percentile of all amounts.
--    Reports alert volume, fraud captured, and the resulting precision.
-- ---------------------------------------------------------------------------
WITH threshold AS (
    SELECT PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY amount) AS p99
    FROM transactions
)
SELECT
    (SELECT ROUND(p99::numeric, 2) FROM threshold)                 AS threshold_amount,
    COUNT(*)                                                     AS alerts,
    SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END)                   AS fraud_captured,
    ROUND(100.0 * SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*), 0), 2)                              AS precision_pct,
    ROUND(100.0 * SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END)
          / NULLIF((SELECT COUNT(*) FROM transactions WHERE class = 1), 0), 2)
                                                                 AS recall_pct
FROM transactions
CROSS JOIN threshold
WHERE amount > threshold.p99;

-- ---------------------------------------------------------------------------
-- 2. Alert-precision ladder across amount percentiles — the reviewer-workload
--    trade-off at several thresholds (CTE + window over a ranked frame).
-- ---------------------------------------------------------------------------
WITH ranked AS (
    SELECT
        class,
        amount,
        PERCENT_RANK() OVER (ORDER BY amount) AS pct_rank
    FROM transactions
)
SELECT
    threshold_pct,
    COUNT(*)                                             AS alerts,
    SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END)           AS fraud_captured,
    ROUND(100.0 * SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*), 0), 2)                      AS precision_pct,
    ROUND(100.0 * SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END)
          / (SELECT COUNT(*) FROM transactions WHERE class = 1), 2)
                                                         AS recall_pct
FROM ranked
CROSS JOIN (
    VALUES (0.90), (0.95), (0.97), (0.99), (0.995)
) AS t(threshold_pct)
WHERE pct_rank >= threshold_pct
GROUP BY threshold_pct
ORDER BY threshold_pct;

-- ---------------------------------------------------------------------------
-- 3. Multi-CTE investigation: suspicious-hour analysis.
--    Step A: hourly fraud-rate lift. Step B: list transactions during the
--    highest-lift hours. Demonstrates progressive narrowing with CTEs.
-- ---------------------------------------------------------------------------
WITH hourly AS (
    SELECT
        FLOOR(hour_of_day)                       AS hour,
        COUNT(*)                                     AS txns,
        SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END)   AS fraud,
        ROUND(
            100.0 * SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0)
            / (SELECT AVG(class) FROM transactions), 2
        )                                            AS lift
    FROM transactions
    GROUP BY FLOOR(hour_of_day)
),
suspicious_hours AS (
    SELECT hour, lift
    FROM hourly
    WHERE lift > 150           -- fraud rate at least 1.5x the global rate
),
flagged AS (
    SELECT t.transaction_id, t.transaction_time, t.amount, t.class, s.lift, s.hour
    FROM transactions t
    JOIN suspicious_hours s
      ON FLOOR(t.hour_of_day) = s.hour
)
SELECT
    hour,
    lift,
    COUNT(*)                                AS candidates,
    SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END) AS known_fraud,
    ROUND(AVG(amount), 2)                   AS avg_candidate_amount
FROM flagged
GROUP BY hour, lift
ORDER BY lift DESC;

-- ---------------------------------------------------------------------------
-- 4. Rapid-transaction pattern: transactions arriving within 1 second of the
--    previous one, with the count per 100-second cluster windowed over time.
-- ---------------------------------------------------------------------------
WITH gaps AS (
    SELECT
        transaction_id,
        class,
        amount,
        transaction_time,
        transaction_time
            - LAG(transaction_time) OVER (ORDER BY transaction_time) AS gap_sec
    FROM transactions
)
SELECT
    COUNT(*)                                                          AS rapid_txns,
    COUNT(*) FILTER (WHERE class = 1)                                 AS rapid_fraud,
    ROUND(100.0 * COUNT(*) FILTER (WHERE class = 1) / NULLIF(COUNT(*), 0), 2)
                                                                      AS fraud_share_pct,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY amount)::numeric, 2)
                                                                      AS median_amount
FROM gaps
WHERE gap_sec <= 1;

-- ---------------------------------------------------------------------------
-- 5. Fraud-proximity probe: legitimate transactions occurring within 60
--    seconds of a known fraudulent transaction (LATERAL existence check).
--    These are candidate review items, not fraud verdicts.
-- ---------------------------------------------------------------------------
SELECT
    t.transaction_id,
    t.transaction_time,
    t.amount,
    f.ref_fraud_id,
    ROUND(f.delta_sec::numeric, 1) AS delta_from_fraud_sec
FROM transactions t
CROSS JOIN LATERAL (
    SELECT
        f.transaction_id AS ref_fraud_id,
        f.transaction_time,
        ABS(f.transaction_time - t.transaction_time) AS delta_sec
    FROM transactions f
    WHERE f.class = 1
      AND ABS(f.transaction_time - t.transaction_time) <= 60
      AND f.transaction_id <> t.transaction_id
    ORDER BY delta_sec
    LIMIT 1
) f
WHERE t.class = 0
ORDER BY f.delta_sec ASC
LIMIT 20;

-- ---------------------------------------------------------------------------
-- 6. High-value legitimate outliers: the top 0.5% of legitimate amounts.
--    A practical "manual review" worklist demonstrating the false-alert cost.
-- ---------------------------------------------------------------------------
WITH ranked AS (
    SELECT
        transaction_id,
        amount,
        amount_log,
        PERCENT_RANK() OVER (ORDER BY amount) AS pct_rank
    FROM transactions
    WHERE class = 0
)
SELECT
    transaction_id,
    amount,
    amount_log,
    ROUND(pct_rank::numeric, 4) AS amount_pct_rank
FROM ranked
WHERE pct_rank >= 0.995
ORDER BY amount DESC
LIMIT 20;

-- ---------------------------------------------------------------------------
-- 7. Transaction-amount percentile of every fraudulent txn — how unusual are
--    they *by amount*, and how many fraud txns are in each band.
-- ---------------------------------------------------------------------------
WITH ranked AS (
    SELECT
        class,
        amount,
        PERCENT_RANK() OVER (ORDER BY amount) AS pct_rank
    FROM transactions
    WHERE class = 1
)
SELECT
    CASE WHEN pct_rank < 0.50 THEN 'below_median'
         WHEN pct_rank < 0.90 THEN 'p50_90'
         WHEN pct_rank < 0.99 THEN 'p90_99'
         ELSE 'top_1pct' END                     AS amount_band,
    COUNT(*)                                     AS fraud,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS share_of_fraud_pct,
    ROUND(MIN(amount), 2)                        AS band_min,
    ROUND(MAX(amount), 2)                        AS band_max
FROM ranked
GROUP BY amount_band
ORDER BY MIN(pct_rank);

-- ---------------------------------------------------------------------------
-- 8. Model-based alert worklist (populated in Phase 8). Ranks the top 50
--    transactions by their model fraud probability for analyst review.
-- ---------------------------------------------------------------------------
SELECT
    p.model_name,
    p.transaction_id,
    t.amount,
    t.class,
    p.fraud_probability,
    p.predicted_label,
    p.prediction_timestamp,
    ROW_NUMBER() OVER (PARTITION BY p.model_name
                       ORDER BY p.fraud_probability DESC) AS rank_in_model
FROM model_predictions p
JOIN transactions t USING (transaction_id)
ORDER BY p.fraud_probability DESC
LIMIT 50;

-- ---------------------------------------------------------------------------
-- 9. Alerts by source and status — the monitoring queue (populated Phase 7+).
-- ---------------------------------------------------------------------------
SELECT
    alert_source,
    alert_status,
    COUNT(*)                         AS n,
    ROUND(AVG(risk_score), 4)        AS avg_risk_score,
    ROUND(MAX(risk_score), 4)        AS max_risk_score
FROM fraud_alerts
GROUP BY alert_source, alert_status
ORDER BY alert_source, alert_status;

-- ---------------------------------------------------------------------------
-- 10. Recommended operating point: given a minimum recall target (e.g. 60%),
--     what is the cheapest high-value rule that achieves it? (Percentile scan
--     using the amount-rank CTE.)
--     Expected result: EMPTY. Amount-only rules cannot reach 60% recall here
--     (query 2 shows even p90 tops out ~17% recall), which demonstrates that a
--     single amount threshold is a weak fraud rule for this dataset.
-- ---------------------------------------------------------------------------
WITH ranked AS (
    SELECT
        class,
        amount,
        PERCENT_RANK() OVER (ORDER BY amount) AS pct_rank
    FROM transactions
),
candidates AS (
    SELECT
        threshold_pct,
        SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END)         AS fraud_captured,
        COUNT(*)                                          AS alerts
    FROM ranked
    CROSS JOIN (
        VALUES (0.70), (0.80), (0.85), (0.90), (0.95), (0.99)
    ) AS t(threshold_pct)
    WHERE pct_rank >= threshold_pct
    GROUP BY threshold_pct
)
SELECT
    threshold_pct,
    alerts,
    ROUND(100.0 * alerts / (SELECT COUNT(*) FROM transactions), 3)  AS alert_rate_pct,
    fraud_captured,
    ROUND(100.0 * fraud_captured / (SELECT COUNT(*) FROM transactions WHERE class = 1), 2)
                                                                    AS recall_pct,
    ROUND(100.0 * fraud_captured / NULLIF(alerts, 0), 2)            AS precision_pct
FROM candidates
WHERE 100.0 * fraud_captured / (SELECT COUNT(*) FROM transactions WHERE class = 1) >= 60
ORDER BY alerts
LIMIT 1;