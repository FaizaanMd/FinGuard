# EDA & Statistical Findings — FinGuard Track A (benchmark)

Produced by `src/eda.py` and `notebooks/01_eda.ipynb`. Figures live alongside
this file in `reports/eda/`.

## Scope and honesty rules

- `V1..V28` are anonymized PCA components. No business meaning is assigned to
  them; class differences are reported strictly as *distributional*
  differences of anonymous features.
- `hour_of_day` assumes a 24-hour cycle whose starting phase is unknown. Only
  the *shape* of the pattern is interpreted, never an absolute clock time.
- All results are observations of the ULB benchmark and do not generalize
  automatically to any real institution.

## 1. Class imbalance (chart 01)

| Class | Count | Share |
|---|---:|---:|
| Legitimate | 283,253 | 99.833% |
| Fraud | 473 | 0.167% |

Consequence: accuracy is not an evaluation metric for this project; precision,
recall, F1, PR-AUC, and alert volume are used instead.

## 2. Amount behaviour (chart 02)

| Label | n | mean | median | p25 | p95 | max |
|---|---:|---:|---:|---:|---:|---:|
| Legitimate | 283,253 | 88.41 | 22.00 | 5.67 | 365.00 | 25,691.16 |
| Fraud | 473 | 123.87 | 9.82 | 1.00 | 655.82 | 2,125.87 |

- **Median differs from mean by class.** Fraud has a *higher mean* (123.9 vs
  88.4) but a *lower median* (9.8 vs 22.0) — driven by skew on both sides.
  Reporting only one statistic would mislead, so both are always shown.
- Mann-Whitney U on `amount` and `amount_log`: statistically significant
  (p ≈ 2.7e-5) but the practical effect is small — amount alone is a weak
  discriminator.

## 3. Amount deciles (chart 03)

- Smallest-amount decile → **highest fraud rate** (0.58%).
- Fraud rate is elevated again in the top decile (0.29%).
- Result is a mild U-shape; fraud is not concentrated at high amounts.

## 4. Derived time cycle (chart 04)

- Lowest transaction volume and **highest relative fraud rate** in the first
  hours of the derived cycle (0–9h), strongest in 0–3h (~2× global rate).
- Volume peaks mid-cycle; relative fraud rate declines after 9h.
- Day 1 fraud rate 0.189% vs day 2 0.144%.

## 5. Anonymous features (charts 05–06)

Strongest class separators by |Cohen's d|:

| Feature | fraud mean | legit mean | Cohen's d |
|---|---:|---:|---:|
| V14 | −6.84 | 0.01 | **−2.23** |
| V4 | +4.47 | −0.01 | +1.98 |
| V12 | −6.10 | 0.01 | −1.85 |
| V11 | +3.72 | −0.01 | +1.84 |
| V10 | −5.45 | 0.01 | −1.60 |

These components show strong, mostly unimodal class separation — the primary
material for supervised modelling. Correlations among top separators are
moderate (heatmap 05); no V feature is highly collinear with `amount_log`.

## 6. Implications for later phases

1. Rule-based detection on amounts alone is weak (confirmed in SQL phase: p90
   rule ≈ 17% recall). Rules will be positioned as explainable baselines.
2. Supervised models (Phase 8) should consume the V-features (and engineered
   columns), mirroring the SQL feature separation result.
3. PR-AUC and threshold analysis (Phase 8/11) are the right evaluation lens for
   a 0.167% base rate.

## 7. Limitations

- Anonymized features prevent cause-level interpretation.
- Duplicate handling removed 19 fraud rows (documented in cleaning phase).
- No customer, merchant, device, or location identifiers exist to support
  velocity/geography rules in Track A (Track B synthetic data covers those).