# Feature Engineering Documentation — Track A (benchmark)

Input: `data/processed/transactions_cleaned.csv` (283,726 rows × 32 cols).
Output: `data/processed/features_engineered.csv` (283,726 rows × 35 cols).

## Pipeline

```
python -m src.data_cleaning        # -> transactions_cleaned.csv
python -m src.feature_engineering  # -> features_engineered.csv
```

## Cleaning decisions

| Rule | Decision | Rationale |
|---|---|---|
| Missing values | None present — nothing to impute | Schema has zero nulls |
| Duplicate rows | Dropped (config `DROP_DUPLICATES = True`) | 1,081 exact duplicates removed, including 19 fraud rows (−3.9% of fraud). Deduplication protects random train/test splits from row leakage. Configurable; if disabled, use a duplicate-aware split at modelling time |
| Noisy/invalid amounts | None — all non-negative, none null | — |
| transaction_id | Integer 1..N assigned | Stable join key for features, alerts, and SQL loading |

## Features added

| Feature | Formula | Assumption & usage |
|---|---|---|
| `hour_of_day` | `(Time % 86400) / 3600` | Treats `Time` as relative seconds over a ~48 h window with a 24 h daily cycle. The cycle *phase* is unknown (start instant is not midnight), so only the shape of the diurnal pattern is interpretable — never an absolute clock time. |
| `day_index` | `floor(Time / 86400)` ∈ {0, 1} | Splits the two observed days; confirms both days are present. |
| `amount_log` | `log1p(Amount)` | Compresses the right-skewed amount distribution for models sensitive to scale/extremes. Raw `Amount` is retained alongside it. |

## Deliberately NOT done here

- **Feature scaling** of `Amount`/`amount_log`. Any scaler (StandardScaler,
  RobustScaler, etc.) must be fit **on the training split only** inside the
  modelling pipeline to avoid test/train leakage. The anonymized `V1..V28`
  features are already PCA-unit-scaled.
- **Customer/merchant/velocity features.** The benchmark has no customer,
  merchant, device, or location identifiers. Manufacturing such features is
  unsupported and would be dishonest. (Track B — the synthetic dataset — will
  demonstrate those analytically.)

## Feature list (35 columns)

`transaction_id`, `Time`, `V1`–`V28`, `Amount`, `Class`,
`hour_of_day`, `day_index`, `amount_log`