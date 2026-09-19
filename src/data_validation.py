"""Data quality and schema validation for FinGuard.

The checks here are deliberately general so they can be reused by the cleaning
pipeline and by automated tests:

- required-column validation
- missing-value detection
- duplicate detection
- amount range checks
- target-label validation
- data-type checks

A `ValidationReport` (JSON-friendly dict) is produced, and the module can be
run directly to print a summary:
    python -m src.data_validation
"""
from __future__ import annotations

import pandas as pd
from pathlib import Path

from src.config import (
    CREDITCARD_FEATURE_COLUMNS,
    CREDITCARD_TARGET_COLUMN,
    CREDITCARD_AMOUNT_COLUMN,
    CREDITCARD_TIME_COLUMN,
    RAW_CREDITCARD_PATH,
)

REQUIRED_COLUMNS = (
    CREDITCARD_FEATURE_COLUMNS
    + [CREDITCARD_TIME_COLUMN, CREDITCARD_AMOUNT_COLUMN, CREDITCARD_TARGET_COLUMN]
)


def validate_columns(df: pd.DataFrame) -> dict:
    """Check that all required columns exist."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    extra = [c for c in df.columns if c not in REQUIRED_COLUMNS]
    return {
        "check": "required_columns",
        "status": "PASS" if not missing else "FAIL",
        "missing_columns": missing,
        "extra_columns": extra,
    }


def validate_missing_values(df: pd.DataFrame) -> dict:
    """Count nulls per column."""
    nulls = df.isnull().sum()
    has_null = bool(nulls.any())
    return {
        "check": "missing_values",
        "status": "PASS" if not has_null else "WARN",
        "total_cells": int(df.size),
        "null_cells": int(nulls.sum()),
        "nulls_by_column": {
            col: int(v) for col, v in nulls.items() if int(v) > 0
        },
    }


def validate_duplicates(df: pd.DataFrame) -> dict:
    """Count fully-duplicate rows."""
    n_dup = int(df.duplicated().sum())
    return {
        "check": "duplicate_rows",
        "status": "PASS" if n_dup == 0 else "WARN",
        "duplicate_count": n_dup,
        "duplicate_rate": round(n_dup / len(df), 6) if len(df) else None,
    }


def validate_amounts(df: pd.DataFrame) -> dict:
    """Amounts must be present and non-negative."""
    col = CREDITCARD_AMOUNT_COLUMN
    n_null = int(df[col].isnull().sum())
    n_negative = int((df[col] < 0).sum())
    return {
        "check": "amount_range",
        "status": "PASS" if n_null == 0 and n_negative == 0 else "FAIL",
        "null_amounts": n_null,
        "negative_amounts": n_negative,
    }


def validate_labels(df: pd.DataFrame) -> dict:
    """Target labels must be exactly {0, 1}."""
    col = CREDITCARD_TARGET_COLUMN
    unique = sorted(df[col].dropna().unique().tolist())
    ok = set(unique) <= {0, 1}
    return {
        "check": "target_labels",
        "status": "PASS" if ok else "FAIL",
        "unique_labels": unique,
    }


def validate_dtypes(df: pd.DataFrame) -> dict:
    """Float features / amount, int target — reject object columns."""
    bad = [
        c
        for c in REQUIRED_COLUMNS
        if c in df.columns and not pd.api.types.is_numeric_dtype(df[c])
    ]
    return {
        "check": "column_dtypes",
        "status": "PASS" if not bad else "FAIL",
        "non_numeric_columns": bad,
    }


def build_report(df: pd.DataFrame) -> dict:
    """Run every check and return a JSON-friendly combined report."""
    if df.empty:
        return {"status": "FAIL", "check": "empty_frame", "rows": 0}

    checks = [
        validate_columns(df),
        validate_dtypes(df),
        validate_missing_values(df),
        validate_duplicates(df),
        validate_amounts(df),
        validate_labels(df),
    ]
    overall = "PASS" if all(c["status"] == "PASS" for c in checks) else (
        "WARN" if any(c["status"] == "WARN" for c in checks) else "FAIL"
    )
    counts = df[CREDITCARD_TARGET_COLUMN].value_counts().sort_index()
    return {
        "status": overall,
        "checks": checks,
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "class_counts": {str(k): int(v) for k, v in counts.items()},
        "fraud_rate": round(float(counts.get(1, 0)) / len(df), 6),
    }


def print_report(report: dict) -> None:
    """Pretty-print a build_report() result."""
    print("Data Quality Report")
    print("-" * 50)
    print(f"Rows: {report['rows']:,}  Columns: {report['columns']}")
    print(f"Overall status: {report['status']}")
    for check in report["checks"]:
        print(f"  [{check['status']}] {check['check']}")
    print("-" * 50)


if __name__ == "__main__":
    path = Path(RAW_CREDITCARD_PATH)
    if not path.exists():
        raise SystemExit(f"Raw data not found at {path}")
    frame = pd.read_csv(path)
    print_report(build_report(frame))
    print(f"\nClass distribution:\n{frame[CREDITCARD_TARGET_COLUMN].value_counts()}")
    print(f"\nFraud rate: {100 * frame[CREDITCARD_TARGET_COLUMN].mean():.4f}%")