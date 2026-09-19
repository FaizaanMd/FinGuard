"""Tests for src.data_cleaning."""
from __future__ import annotations

import numpy as np

from src.data_cleaning import clean
from src.config import CREDITCARD_AMOUNT_COLUMN, CREDITCARD_TARGET_COLUMN
from tests.helpers import make_synthetic_raw


def test_clean_assigns_sequential_ids():
    cleaned, report = clean(make_synthetic_raw())
    assert cleaned["transaction_id"].tolist() == list(range(1, len(cleaned) + 1))


def test_clean_drops_duplicates_and_reports_fraud_impact():
    raw = make_synthetic_raw(dup_rows=11)
    cleaned, report = clean(raw, drop_duplicates=True)
    assert report["dropped_duplicates"] == 11
    assert report["output_rows"] == report["input_rows"] - 11
    assert report["dropped_duplicate_fraud_rows"] <= report["fraud_rows_before"]


def test_clean_skips_dedup_when_disabled():
    raw = make_synthetic_raw(dup_rows=7)
    cleaned, report = clean(raw, drop_duplicates=False)
    assert report["dropped_duplicates"] == 0
    assert report["output_rows"] == report["input_rows"]


def test_clean_preserves_class_balance():
    cleaned, report = clean(make_synthetic_raw())
    assert report["fraud_rows_before"] == report["fraud_rows_after"]
    assert set(cleaned[CREDITCARD_TARGET_COLUMN].unique()) <= {0, 1}


def test_clean_keeps_amounts_unchanged():
    raw = make_synthetic_raw()
    cleaned, _ = clean(raw)
    np.testing.assert_allclose(
        cleaned[CREDITCARD_AMOUNT_COLUMN], raw[CREDITCARD_AMOUNT_COLUMN])


def test_clean_raises_when_validation_fails():
    raw = make_synthetic_raw()
    raw.iloc[0, raw.columns.get_loc("Class")] = 7
    try:
        clean(raw)
    except ValueError:
        return
    raise AssertionError("clean() should reject invalid raw data")