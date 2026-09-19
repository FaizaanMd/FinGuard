# SQL Analytics Summary — FinGuard (Track A benchmark)

Files: `sql/exploratory_queries.sql` (13 queries) + `sql/business_queries.sql`
(10 queries). Re-run with `python scripts/run_sql_analytics.py`.

All results below are **observations about the anonymized ULB benchmark**, not
claims about real fraud operations.

## Fraud fundamentals

| Metric | Value |
|---|---:|
| Transactions | 283,726 |
| Fraud | 473 |
| Fraud rate | 0.1667% |

## Amount findings

- **Legitimate** amounts: median **22.00**, mean higher, max 25,691.16.
- **Fraud** amounts: median **9.82**, max 2,125.87.
- Fraud is concentrated at the *low* end of the amount range:
  - 82.66% of fraud lies in the bottom 90% of amounts.
  - 49.89% of fraud is below the overall median amount.
  - Only 1.90% of fraud is in the top 1% of amounts.
- Decile view shows a **U-shape**: fraud rate is highest in the smallest-amount
  decile (0.58%) and also mildly elevated in the largest-amount decile (0.29%).
- **Consequence:** a single "high-value" rule is a weak fraud detector — see
  the precision ladder (business Q2): the p90 amount threshold captures only
  ~17% of fraud at <0.3% precision. No amount threshold reaches 60% recall
  (business Q10 returns empty on purpose).
- Some of the fastest gaps between transactions are legitimate six-figure
  amounts arriving in the same second (exploratory Q13) — identical-time
  high-value transactions exist in the legit class, so time-gap rules must be
  combined with other signals, never applied alone.

## Time-cycle findings (derived `hour_of_day`, phase unknown)

- The first 6 hours of the derived daily cycle carry the highest fraud rate
  (0.48%, **2.9×** the global rate); the rest of the day drops below or near
  the global rate (business Q3 identifies hours 2–7 as top-lift).
- Day 1 has a higher fraud rate (0.189%) than day 2 (0.144%).

## Feature separation (anonymized PCs)

Standardized mean differences (Cohen's d, exploratory Q7) show several PCs
separate the classes strongly:

| Feature | Fraud mean | Legit mean | Cohen's d |
|---|---:|---:|---:|
| v14 | −6.836 | 0.012 | **−2.23** |
| v12 | −6.103 | 0.010 | −1.85 |
| v10 | −5.453 | 0.008 | −1.60 |
| v04 | +4.473 | −0.010 | +1.99 |

These anonymized components are the strongest separators — amounts alone are
not — which motivates feature-driven ML over rules in Phases 7–8.

## Investigation-workflow examples (business file)

- Business Q1/Q2 — baseline alert (amount > p99): 2,838 alerts for **9** fraud
  rows → 0.32% precision, 1.90% recall → high reviewer workload, low yield.
- Business Q3 — suspicious-hour CTE chain narrows the candidate pool by season.
- Business Q5 — legitimate transactions within 60 s of a known fraud: a manual
  review worklist (proximity ≠ fraud).
- Business Q6 — top 0.5% legitimate amounts: the false-alert cost made visible.
- Business Q8/Q9 — alert-worklist and status-queue queries that populate once
  `model_predictions` / `fraud_alerts` exist (Phases 7–8).

## Interview talking points

1. **CTEs** chain investigation steps (business Q3, Q10).
2. **Window functions**: `LAG` (time gaps), `NTILE` (deciles), `PERCENT_RANK`
   (percentile ladders), `ROW_NUMBER` (model ranking).
3. **LATERAL + VALUES** pivots 28 columns into rows for one-pass comparisons
   (exploratory Q7).
4. **Trade-off framing**: every threshold is a *workload vs. yield* decision,
   shown as precision/recall ladders rather than raw accuracy.
5. Pitfall discovered: PostgreSQL `::int` **rounds** float→int; use `FLOOR` for
   binning (documented in exploratory Q3).