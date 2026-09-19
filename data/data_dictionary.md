# Data Dictionary — Credit Card Fraud Detection (Track A)

**Source:** Machine Learning Group — Université Libre de Bruxelles (ULB), via
[Kaggle](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud).
Transactions by European cardholders over two days in September 2013.

**Licence:** Open Data Commons Database License (ODbL) 1.0 per Kaggle.

**Integrity:** `creditcard.csv` SHA-256 =
`76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89`
(verified against the mirror's documented hash).

## Schema (284,807 rows × 31 columns)

| Column | Type | Description |
|---|---|---|
| `Time` | numeric | Seconds elapsed between the first transaction and this transaction (relative, not wall-clock). | 
| `V1` … `V28` | float | Principal-component-transformed features of the original (undisclosed) attributes. **Anonymized** — no business meaning is claimed for them. |
| `Amount` | float | Transaction amount in the original currency (untransformed). |
| `Class` | int (0/1) | Target: 1 = fraudulent, 0 = legitimate. |

## Data-quality findings (Phase 2 validation)

| Check | Result |
|---|---|
| Required columns | PASS — all 31 present, no extras |
| Data types | PASS — all numeric |
| Missing values | PASS — zero nulls across all columns |
| Duplicate rows | WARN — 1,081 full-row duplicates |
| Amount range | PASS — no null/negative amounts |
| Target labels | PASS — only {0, 1} |

### Class imbalance

| Class | Count | Share |
|---|---:|---:|
| 0 — legitimate | 284,315 | 99.8273 % |
| 1 — fraud | 492 | 0.1727 % |

### Duplicate nuance

1,081 rows are exact duplicates; **19 of them are fraud** (3.86% of all fraud).
This is a known quirk of the dataset, so the duplicate-handling decision in
Phase 3 must weigh removing noise against losing fraud observations — and must
be documented regardless of the choice.

### Feature-scaling note

`Amount` (raw € amounts) is unbounded while `V1`…`V28` are already PCA-scaled,
so `Amount` will need scaling before distance/regularised models, and `Time` is
relative seconds (feature engineering will treat it as such).

## Guidance

Do **not** invent business meanings for `V1`…`V28`. Only `Time`, `Amount`, and
`Class` are interpretable; all pattern claims for hidden PCs will be framed
strictly as "anonymous feature X shows a distributional difference" or derived
statistics between classes.