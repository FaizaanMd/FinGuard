# Dataset

## Track A — Benchmark dataset

The benchmark uses the publicly available **Credit Card Fraud Detection**
dataset (anonymized features `V1..V28`, `Time`, `Amount`, `Class`).

Downloaded 2026-09-19 from the HuggingFace mirror of the Kaggle dataset:

```
https://huggingface.co/datasets/David-Egea/Creditcard-fraud-detection
```

SHA-256 verified against the mirror's documented hash:
`76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89`.
The ULB-hosted mirror is no longer reliably reachable.

The raw file (`creditcard.csv`, ~151 MB) is **not committed** to the
repository for size and licensing reasons. See `data_dictionary.md` for schema
and the Phase 2 data-quality findings.

## Track B — Business simulation

A clearly-labelled **synthetic** transaction dataset (customer_id, merchant
category, velocity, etc.) used to demonstrate operational analytics and
monitoring workflows. It does **not** represent real banking data and generated
patterns will not be presented as findings from a financial institution.

See: [Project blueprint §6](README) for the dataset strategy.