-- ============================================================================
-- FinGuard — exploratory SQL analytics (Track A benchmark)
-- Target: PostgreSQL 17, database: finguard, table: transactions
-- Run:   psql -h localhost -U postgres -d finguard -f sql/exploratory_queries.sql
--
-- Every query is written to answer a *meaningful* question against the data
-- that actually exists: anonymized V-features, relative Time, Amount, Class,
-- plus the engineered hour_of_day / day_index / amount_log.
--
-- Interpretation caveat: patterns here are dataset observations for an
-- anonymized benchmark, not claims about real banking operations.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. Overall fraud rate
-- ---------------------------------------------------------------------------
SELECT
    COUNT(*)                                                 AS total,
    SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END)               AS fraud,
    ROUND(100.0 * SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*), 0), 4)                          AS fraud_rate_pct
FROM transactions;

-- ---------------------------------------------------------------------------
-- 2. Transaction-amount distribution by label (percentiles + mean vs median)
-- ---------------------------------------------------------------------------
SELECT
    class,
    COUNT(*)                                                AS n,
    ROUND(AVG(amount), 2)                                   AS mean_amount,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY amount)::numeric, 2)
                                                            AS median_amount,
    ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY amount)::numeric, 2)
                                                            AS q25_amount,
    ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY amount)::numeric, 2)
                                                            AS q75_amount,
    ROUND(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY amount)::numeric, 2)
                                                            AS q99_amount,
    ROUND(MAX(amount), 2)                                   AS max_amount
FROM transactions
GROUP BY class
ORDER BY class;

-- ---------------------------------------------------------------------------
-- 3. Fraud rate by 6-hour band of the derived daily cycle (hour_of_day).
--    Uses FLOOR (PostgreSQL ::int rounds, which would skew the bands).
--    'lift' compares each band's fraud rate to the global fraud rate.
-- ---------------------------------------------------------------------------
WITH global_rate AS (
    SELECT AVG(class) AS rate
    FROM transactions
),
bands AS (
    SELECT
        class,
        FLOOR(hour_of_day / 6) * 6 AS band_start,
        FLOOR(hour_of_day / 6) * 6 + 6 AS band_end
    FROM transactions
)
SELECT
    band_start,
    band_end,
    COUNT(*)                                                     AS txns,
    SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END)                   AS fraud,
    ROUND(100.0 * SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*), 0), 4)                              AS band_fraud_rate_pct,
    ROUND(
        100.0 * SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0)
        / (SELECT rate FROM global_rate), 2
    )                                                            AS lift_vs_global
FROM bands
GROUP BY band_start, band_end
ORDER BY band_start;

-- ---------------------------------------------------------------------------
-- 4. Per-day summary (the window covers two days)
-- ---------------------------------------------------------------------------
SELECT
    day_index,
    COUNT(*)                                               AS txns,
    SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END)             AS fraud,
    ROUND(100.0 * SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*), 0), 4)                        AS fraud_rate_pct
FROM transactions
GROUP BY day_index
ORDER BY day_index;

-- ---------------------------------------------------------------------------
-- 5. Time-gap analysis: seconds since the previous transaction.
--    Window function LAG over the timeline; gap stats by the *current* label.
-- ---------------------------------------------------------------------------
WITH gaps AS (
    SELECT
        class,
        transaction_time
            - LAG(transaction_time) OVER (ORDER BY transaction_time) AS gap_sec
    FROM transactions
)
SELECT
    class,
    COUNT(gap_sec)                                  AS n_gaps,
    ROUND(AVG(gap_sec)::numeric, 1)                 AS mean_gap_sec,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY gap_sec)::numeric, 1)
                                                    AS median_gap_sec,
    ROUND(PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY gap_sec)::numeric, 1)
                                                    AS p05_gap_sec
FROM gaps
GROUP BY class
ORDER BY class;

-- ---------------------------------------------------------------------------
-- 6. Fraud concentration across amount deciles (NTILE window function).
--    Checks whether fraud concentrates in specific parts of the amount range.
-- ---------------------------------------------------------------------------
WITH deciles AS (
    SELECT
        class,
        amount,
        NTILE(10) OVER (ORDER BY amount) AS decile
    FROM transactions
)
SELECT
    decile,
    COUNT(*)                                        AS txns,
    SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END)      AS fraud,
    ROUND(100.0 * SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*), 0), 4)                 AS fraud_rate_pct,
    ROUND(MAX(amount), 2)                           AS band_max_amount
FROM deciles
GROUP BY decile
ORDER BY decile;

-- ---------------------------------------------------------------------------
-- 7. V-feature class separation, ranked by standardized mean difference
--    (Cohen's d). LATERAL + VALUES pivot the 28 columns into rows, then one
--    GROUP BY computes both classes' mean and standard deviation per feature.
-- ---------------------------------------------------------------------------
WITH class_stats AS (
    SELECT
        feat,
        AVG(CASE WHEN class = 1 THEN val END)     AS fraud_mean,
        AVG(CASE WHEN class = 0 THEN val END)     AS legit_mean,
        STDDEV(CASE WHEN class = 1 THEN val END)  AS fraud_sd,
        STDDEV(CASE WHEN class = 0 THEN val END)  AS legit_sd
    FROM transactions
    CROSS JOIN LATERAL (
        VALUES
            ('v01', v1),  ('v02', v2),  ('v03', v3),  ('v04', v4),
            ('v05', v5),  ('v06', v6),  ('v07', v7),  ('v08', v8),
            ('v09', v9),  ('v10', v10), ('v11', v11), ('v12', v12),
            ('v13', v13), ('v14', v14), ('v15', v15), ('v16', v16),
            ('v17', v17), ('v18', v18), ('v19', v19), ('v20', v20),
            ('v21', v21), ('v22', v22), ('v23', v23), ('v24', v24),
            ('v25', v25), ('v26', v26), ('v27', v27), ('v28', v28)
    ) AS pivot(feat, val)
    GROUP BY feat
)
SELECT
    feat,
    ROUND(fraud_mean::numeric, 4)  AS fraud_mean,
    ROUND(legit_mean::numeric, 4)  AS legit_mean,
    ROUND((fraud_mean - legit_mean)::numeric, 4)   AS mean_diff,
    ROUND(
        ((fraud_mean - legit_mean)
        / NULLIF(SQRT((fraud_sd * fraud_sd + legit_sd * legit_sd) / 2.0), 0))::numeric,
        4
    )                                              AS cohens_d
FROM class_stats
ORDER BY ABS(fraud_mean - legit_mean) DESC
LIMIT 8;

-- ---------------------------------------------------------------------------
-- 8. Largest fraudulent transactions (investigation seeds)
-- ---------------------------------------------------------------------------
SELECT
    transaction_id,
    transaction_time,
    hour_of_day,
    amount,
    amount_log
FROM transactions
WHERE class = 1
ORDER BY amount DESC
LIMIT 10;

-- ---------------------------------------------------------------------------
-- 9. Largest legitimate transactions — the alert-volume side of the trade-off
-- ---------------------------------------------------------------------------
SELECT
    transaction_id,
    transaction_time,
    amount,
    amount_log
FROM transactions
WHERE class = 0
ORDER BY amount DESC
LIMIT 10;

-- ---------------------------------------------------------------------------
-- 10. Activity density through the day (2-hour buckets, shares of total)
-- ---------------------------------------------------------------------------
SELECT
    (hour_of_day / 2)::int * 2                   AS bin_start,
    (hour_of_day / 2)::int * 2 + 2               AS bin_end,
    COUNT(*)                                     AS txns,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 3) AS share_pct
FROM transactions
GROUP BY bin_start, bin_end
ORDER BY bin_start;

-- ---------------------------------------------------------------------------
-- 11. Amount-band extremes: what share of fraud sits in the top 1% of amounts?
-- ---------------------------------------------------------------------------
WITH ranked AS (
    SELECT
        class,
        amount,
        PERCENT_RANK() OVER (ORDER BY amount) AS amount_pct_rank
    FROM transactions
)
SELECT
    CASE WHEN amount_pct_rank >= 0.99 THEN 'top_1pct'
         WHEN amount_pct_rank >= 0.95 THEN '95_99'
         WHEN amount_pct_rank >= 0.90 THEN '90_95'
         ELSE 'bottom_90' END                          AS amount_band,
    COUNT(*)                                          AS txns,
    SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END)        AS fraud,
    ROUND(100.0 * SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*), 0), 4)                   AS fraud_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END)
          / SUM(SUM(CASE WHEN class = 1 THEN 1 ELSE 0 END)) OVER (), 2)
                                                      AS share_of_all_fraud_pct
FROM ranked
GROUP BY amount_band
ORDER BY MIN(amount_pct_rank);

-- ---------------------------------------------------------------------------
-- 12. Skew check: mean vs median of amount_log by class
-- ---------------------------------------------------------------------------
SELECT
    class,
    ROUND(AVG(amount_log)::numeric, 4)   AS mean_log_amount,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY amount_log)::numeric, 4)
                                         AS median_log_amount,
    ROUND(MAX(amount_log)::numeric, 4)   AS max_log_amount
FROM transactions
GROUP BY class
ORDER BY class;

-- ---------------------------------------------------------------------------
-- 13. Transactions with the shortest time gaps (rapid-fire pattern probe)
--    Window function: gaps <= 1 second, ordered by amount desc.
-- ---------------------------------------------------------------------------
WITH gaps AS (
    SELECT
        transaction_id,
        transaction_time,
        class,
        amount,
        transaction_time
            - LAG(transaction_time) OVER (ORDER BY transaction_time) AS gap_sec
    FROM transactions
)
SELECT
    transaction_id,
    transaction_time,
    class,
    amount,
    ROUND(gap_sec::numeric, 2) AS gap_sec
FROM gaps
WHERE gap_sec <= 1
ORDER BY gap_sec, amount DESC
LIMIT 15;