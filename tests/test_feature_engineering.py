"""Tests for src.feature_engineering."""
from __future__ import annotations

import numpy as np

from src.feature_engineering import (
    DERIVED_FEATURES,
    SECONDS_PER_DAY,
    add_amount_features,
    add_time_features,
    build_features,
)
from tests.helpers import make_synthetic_raw


def test_time_features_respect_wraparound():
    frame = make_synthetic_raw(n=5, seed=1)
    frame["Time"] = np.array([0.0, 3_600.0, 86_400.0, 90_000.0, 172_800.0])
    out = add_time_features(frame)
    np.testing.assert_allclose(
        out["hour_of_day"], [0.0, 1.0, 0.0, 1.0, 0.0])
    np.testing.assert_array_equal(
        out["day_index"], [0, 0, 1, 1, 2])


def test_hour_of_day_bounded_in_synthetic_data():
    frame = add_time_features(make_synthetic_raw(n=400, seed=2))
    assert (frame["hour_of_day"] >= 0).all()
    assert (frame["hour_of_day"] < 24).all()
    assert set(frame["day_index"].unique()) <= {0, 1, 2}


def test_amount_log_is_log1p():
    frame = add_amount_features(make_synthetic_raw(n=50, seed=3))
    expected = np.log1p(frame["Amount"])
    np.testing.assert_allclose(frame["amount_log"], expected)
    assert (frame["amount_log"] >= 0).all()


def test_build_features_adds_expected_columns():
    out = build_features(make_synthetic_raw(n=100, seed=4))
    for column in DERIVED_FEATURES:
        assert column in out.columns
    assert "Time" in out.columns and "Amount" in out.columns


def test_seconds_per_day_constant():
    assert SECONDS_PER_DAY == 86_400