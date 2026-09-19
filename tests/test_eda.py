"""Tests for src.eda statistical helpers (no plotting, no data files)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.eda import (
    amount_stats,
    cohens_d_ranking,
    imbalance_summary,
    load,
    statistical_tests,
    time_patterns,
)
from src.config import ENGINEERED_FEATURES_PATH
from tests.helpers import make_engineered_frame


def test_imbalance_summary_shares_sum_to_100():
    summary = imbalance_summary(make_engineered_frame(n=1500, seed=30))
    assert list(summary["label"]) == ["legitimate", "fraud"]
    np.testing.assert_allclose(summary["share_pct"].sum(), 100.0, rtol=1e-9)


def test_amount_stats_reports_both_classes():
    stats = amount_stats(make_engineered_frame(n=1500, seed=31))
    assert len(stats) == 2
    assert (stats["p25"] <= stats["median"]).all()
    assert (stats["median"] <= stats["p75"]).all()


def test_cohens_d_ranking_returns_descending_abs():
    ranking = cohens_d_ranking(make_engineered_frame(n=1500, seed=32))
    assert set(ranking.columns) == {
        "feature", "fraud_mean", "legit_mean", "cohens_d"}
    assert len(ranking) <= 8
    abs_d = ranking["cohens_d"].abs().tolist()
    assert abs_d == sorted(abs_d, reverse=True)


def test_synthetic_v14_has_negative_cohens_d():
    frame = make_engineered_frame(n=3000, seed=33)
    ranking = cohens_d_ranking(frame, top_n=28)
    row = ranking.loc[ranking["feature"] == "V14"].iloc[0]
    assert row["cohens_d"] < -1.0  # synthetic signal injected in helpers


def test_time_patterns_include_lift():
    patterns = time_patterns(make_engineered_frame(n=1500, seed=34))
    assert "lift" in patterns.columns
    assert "hour_band" in patterns.columns
    assert (patterns["txns"] > 0).all()


def test_statistical_tests_report_pvalues():
    results = statistical_tests(make_engineered_frame(n=1500, seed=35))
    assert len(results) == 2
    for entry in results:
        assert 0 <= entry["p_value"] <= 1


def test_load_raises_for_missing_file(tmp_path):
    missing = tmp_path / "nope.csv"
    try:
        load(missing)
    except FileNotFoundError:
        return
    raise AssertionError("load() should raise for a missing file")


def test_load_reads_existing_csv(tmp_path):
    path = tmp_path / "frame.csv"
    make_engineered_frame(n=100, seed=36).to_csv(path, index=False)
    frame = load(path)
    assert len(frame) == 100
    assert "transaction_id" in frame.columns