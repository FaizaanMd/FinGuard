"""Data cleaning pipeline for the benchmark transactions dataset.

Responsibilities:
- load the raw CSV and run the data-quality checks from data_validation
- apply configured cleaning rules (duplicate handling is configurable)
- assign a stable integer transaction_id
- persist the cleaned dataset to data/processed/

Design decisions are reported alongside the output so the cleaning step is
auditable: row counts before/after each rule and the number of fraud rows
affected by duplicate removal.

Run directly:
    python -m src.data_cleaning
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src import data_validation as validation
from src.config import (
    CLEANED_TRANSACTIONS_PATH,
    CREDITCARD_AMOUNT_COLUMN,
    CREDITCARD_TARGET_COLUMN,
    DROP_DUPLICATES,
    RAW_CREDITCARD_PATH,
)

LOGGER = logging.getLogger("finguard.cleaning")


def load_raw(path: Path = RAW_CREDITCARD_PATH) -> pd.DataFrame:
    """Read the raw CSV, raising a clear error if it is absent."""
    if not Path(path).exists():
        raise FileNotFoundError(
            f"Raw dataset not found at {path}. See data/README.md."
        )
    return pd.read_csv(path)


def clean(
    raw: pd.DataFrame,
    drop_duplicates: bool = DROP_DUPLICATES,
) -> tuple[pd.DataFrame, dict]:
    """Apply cleaning rules and return (cleaned_frame, report)."""
    report = {"input_rows": int(len(raw))}

    validation_summary = validation.build_report(raw)
    report["validation_status"] = validation_summary["status"]
    if validation_summary["status"] == "FAIL":
        raise ValueError("Raw data failed validation; see report.")

    frame = raw.copy()

    fraud_before = int((frame[CREDITCARD_TARGET_COLUMN] == 1).sum())

    if drop_duplicates:
        is_dup = frame.duplicated(keep="first")
        dropped = int(is_dup.sum())
        dropped_fraud = int((frame.loc[is_dup, CREDITCARD_TARGET_COLUMN] == 1).sum())
        frame = frame.loc[~is_dup].reset_index(drop=True)
        report["dropped_duplicates"] = dropped
        report["dropped_duplicate_fraud_rows"] = dropped_fraud
    else:
        report["dropped_duplicates"] = 0
        report["dropped_duplicate_fraud_rows"] = 0

    report["output_rows"] = int(len(frame))
    report["fraud_rows_before"] = fraud_before
    report["fraud_rows_after"] = int((frame[CREDITCARD_TARGET_COLUMN] == 1).sum())

    frame.insert(0, "transaction_id", range(1, len(frame) + 1))

    column_order = ["transaction_id"] + [
        c for c in frame.columns if c != "transaction_id"
    ]
    frame = frame[column_order]

    return frame, report


def save(frame: pd.DataFrame, path: Path = CLEANED_TRANSACTIONS_PATH) -> Path:
    """Persist the cleaned frame to CSV."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return Path(path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    raw = load_raw()
    LOGGER.info("Loaded %s rows", len(raw))

    cleaned, report = clean(raw)
    for key, value in report.items():
        LOGGER.info("%s = %s", key, value)

    out = save(cleaned)
    LOGGER.info("Saved cleaned dataset (%s rows) to %s", len(cleaned), out)

    summary = cleaned[CREDITCARD_TARGET_COLUMN].value_counts().sort_index()
    LOGGER.info("Class distribution:\n%s", summary.to_string())
    LOGGER.info(
        "Amount range: [%.2f, %.2f]",
        cleaned[CREDITCARD_AMOUNT_COLUMN].min(),
        cleaned[CREDITCARD_AMOUNT_COLUMN].max(),
    )