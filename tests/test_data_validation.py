"""Tests for src.data_validation."""
from __future__ import annotations

import pandas as pd

from src import data_validation as validation
from tests.helpers import make_synthetic_raw


def test_report_passes_on_clean_frame():
    report = validation.build_report(make_synthetic_raw())
    assert report["status"] == "PASS"
    assert report["rows"] == 2000


def test_report_detects_missing_column():
    frame = make_synthetic_raw().drop(columns="Time")
    report = validation.build_report(frame)
    assert report["status"] == "FAIL"
    assert report["checks"][0]["check"] == "required_columns"
    assert report["checks"][0]["missing_columns"] == ["Time"]


def test_report_flags_null_labels():
    frame = make_synthetic_raw()
    frame.loc[0, "Class"] = pd.NA
    report = validation.build_report(frame)
    assert report["status"] == "WARN"
    assert report["checks"][2]["check"] == "missing_values"
    assert report["checks"][2]["null_cells"] == 1


def test_report_warns_on_duplicates():
    frame = make_synthetic_raw(dup_rows=5)
    report = validation.build_report(frame)
    assert report["checks"][3]["status"] == "WARN"
    assert report["checks"][3]["duplicate_count"] == 5


def test_report_flags_negative_amounts():
    frame = make_synthetic_raw()
    frame.loc[0, "Amount"] = -1.0
    report = validation.build_report(frame)
    assert report["checks"][4]["status"] == "FAIL"


def test_report_flags_bad_labels():
    frame = make_synthetic_raw()
    frame.loc[0, "Class"] = 3
    report = validation.build_report(frame)
    assert report["checks"][5]["status"] == "FAIL"


def test_report_handles_empty_frame():
    report = validation.build_report(pd.DataFrame())
    assert report["status"] == "FAIL"