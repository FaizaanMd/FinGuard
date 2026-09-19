-- Validation queries for the FinGuard database.
-- Confirm the loaded data matches expectations after `python -m src.db`.

-- 1. Row counts per monitored table
SELECT
    (SELECT COUNT(*) FROM transactions)   AS transactions,
    (SELECT COUNT(*) FROM model_predictions) AS predictions,
    (SELECT COUNT(*) FROM fraud_alerts)   AS alerts;

-- 2. Class distribution and fraud rate
SELECT
    class,
    COUNT(*)                              AS n,
    ROUND(100.0 * COUNT(*) /
          SUM(COUNT(*)) OVER (), 4)       AS share_pct
FROM transactions
GROUP BY class
ORDER BY class;

-- 3. Constraint sanity: no amounts < 0, no labels outside {0,1}, no null keys
SELECT
    SUM(CASE WHEN amount < 0 THEN 1 ELSE 0 END)                  AS bad_amounts,
    SUM(CASE WHEN class NOT IN (0, 1) THEN 1 ELSE 0 END)         AS bad_labels,
    SUM(CASE WHEN transaction_id IS NULL THEN 1 ELSE 0 END)      AS null_ids
FROM transactions;

-- 4. Per-day coverage of the two-day window
SELECT
    day_index,
    COUNT(*)                                 AS n,
    MIN(transaction_time)                    AS first_second,
    MAX(transaction_time)                    AS last_second
FROM transactions
GROUP BY day_index
ORDER BY day_index;

-- 5. Amount statistics by class
SELECT
    class,
    COUNT(*)           AS n,
    MIN(amount)        AS min_amount,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY amount) AS median_amount,
    MAX(amount)        AS max_amount
FROM transactions
GROUP BY class
ORDER BY class;